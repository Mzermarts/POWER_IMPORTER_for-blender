"""Integration tests for 0.6: .blend append, image actions, wildcards and portable settings."""
from pathlib import Path
import sys,uuid,json,hashlib,importlib.util
from unittest.mock import patch
sys.dont_write_bytecode=True
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import bpy,addon_utils
addon_utils.enable('sand3d_browser',default_set=True)
from sand3d_browser import model_io,blend_io,settings_io,thumbnails
root=PROJECT/'test-artifacts'/('v06-'+uuid.uuid4().hex[:10])
source=root/'source'
source.mkdir(parents=True)
image=bpy.data.images.new('Packed fixture',width=64,height=32)
image.pixels=[0.1,0.6,0.8,1.0]*(64*32)
image.filepath_raw=str(source/'image.png')
image.file_format='PNG'
image.save()
image.pack()
mat=bpy.data.materials.new('Blend source material')
node=mat.node_tree.nodes.new('ShaderNodeTexImage')
node.image=image
mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
collection=bpy.data.collections.new('Fixture root')
nested=bpy.data.collections.new('Fixture nested')
collection.children.link(nested)
parent=bpy.data.objects.new('Fixture parent',None)
child=bpy.data.objects.new('Fixture model',bpy.data.objects['Cube'].data.copy())
child.data.materials.clear()
child.data.materials.append(mat)
child.parent=parent
collection.objects.link(parent)
nested.objects.link(child)
child.driver_add('location',0).driver.expression="__import__('builtins').sum([1, 2])"
marker=root/'SCRIPT_MUST_NOT_RUN'
code=bpy.data.texts.new('Embedded script')
code.write('raise RuntimeError("must not execute")')
code.use_module=True
child['embedded_text']=code
blend=source/'model.blend'
bpy.data.libraries.write(str(blend),{collection})
blend_io.check_container(blend)
digest=hashlib.sha256(blend.read_bytes()).hexdigest()
scene=bpy.context.scene
before_objects=set(bpy.data.objects)
old_world,old_camera=scene.world,scene.camera
scene.frame_start,scene.frame_end=17,73
scene.frame_set(28)
wrapper,objects=model_io.import_model(bpy.context,str(source),'model.blend')
assert len(objects)==2
assert any(obj.parent for obj in objects)
assert wrapper['sand3d_muted_complex_drivers']==1
assert before_objects.issubset(set(bpy.data.objects)) and bpy.context.scene==scene
assert (scene.frame_start,scene.frame_end,scene.frame_current)==(17,73,28)
assert scene.world==old_world and scene.camera==old_camera and not marker.exists()
assert hashlib.sha256(blend.read_bytes()).hexdigest()==digest

# Linked-library files must be detected before any native external resolution.
with bpy.data.libraries.load(str(blend),link=True) as (src,dst):
    dst.collections=src.collections
linked=source/'linked.blend'
scene.collection.children.link(dst.collections[0])
bpy.ops.wm.save_as_mainfile(filepath=str(linked),check_existing=False,compress=False)
try:
    blend_io.check_container(linked)
except ValueError as exc:
    assert 'bibliothèques liées' in str(exc)
else:
    raise AssertionError('Linked .blend not detected')

prefs=bpy.context.preferences.addons['sand3d_browser'].preferences
bpy.ops.sand3d.library_add()
prefs.libraries[0].directory=str(source)
prefs.libraries[0].name='Source test 0.6'
bpy.ops.sand3d.index()
state=bpy.context.window_manager.sand3d_state
from sand3d_browser import actions
prefs.prepared_directory=str(root/'prepared')
(root/'prepared').mkdir()
bpy.ops.sand3d.index()
state.query='model.blend'
assert len(state.results)==1
assert bpy.ops.sand3d.prepare_asset()=={'FINISHED'}
process=actions.JOB[0]
process.wait(timeout=45)
actions.refresh_job()
assert process.returncode==0
prepared=Path(actions.READY[actions.key(state.results[0])])
assert prepared.with_suffix('.png').stat().st_size>500
assert prepared.with_suffix('.blend').stat().st_size>1000
assert hashlib.sha256(blend.read_bytes()).hexdigest()==digest
state.query='*.png'
assert len(state.results)==1 and state.results[0].format=='png'
state.format_filter='BLEND'
assert not state.results
state.query='*.blend'
assert len(state.results)==2
state.format_filter='IMAGES'
state.query='*'
assert len(state.results)==1
while thumbnails.QUEUE:
    thumbnails.tick()
assert thumbnails.preview(state.results[0]) is not None

target=bpy.data.objects['Cube']
sibling=target.copy()
scene.collection.objects.link(sibling)
old_mesh=target.data
old_mats=tuple(old_mesh.materials)
old_uv={layer.name:[tuple(v.uv) for v in layer.data] for layer in old_mesh.uv_layers}
bpy.context.view_layer.objects.active=target
assert bpy.ops.sand3d.image_action(action='MATERIAL')=={'FINISHED'}
assert bpy.ops.sand3d.image_action(action='APPLY')=={'FINISHED'}
assert target.data!=old_mesh and sibling.data==old_mesh and tuple(old_mesh.materials)==old_mats
assert old_uv=={layer.name:[tuple(v.uv) for v in layer.data] for layer in target.data.uv_layers}
before_material=target.active_material
state.image_role='NORMAL'
assert bpy.ops.sand3d.image_action(action='NODE')=={'FINISHED'}
assert target.active_material!=before_material
assert any(n.type=='NORMAL_MAP' for n in target.active_material.node_tree.nodes)
before=set(bpy.data.objects)
assert bpy.ops.sand3d.image_action(action='PLANE')=={'FINISHED'}
planes=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
bpy.context.view_layer.update()
assert len(planes)==1 and abs(planes[0].dimensions.y/planes[0].dimensions.x-0.5)<0.00001

# Configuration round trip must not visit any imported library or log path.
data=settings_io.snapshot(prefs)
data['libraries'].append(dict(name='Offline',directory=r'Z:\Offline\Assets',enabled=True,recursive=False,unitless_scale=0.001))
data['general_log']=r'Z:\Offline\general.log'
data['error_log']=r'Z:\Offline\errors.log'
config=root/'settings.json'
settings_io.write(config,data)
with patch.object(Path,'stat',side_effect=AssertionError('Settings apply probed a filesystem path')):
    settings_io.apply(prefs,settings_io.validate(data),merge=False)
assert len(prefs.libraries)==2 and prefs.error_log==data['error_log']
settings_io.apply(prefs,data,merge=True)
assert len(prefs.libraries)==2
unchanged=settings_io.snapshot(prefs)
try:
    settings_io.apply(prefs,dict(data,schema_version=99))
except ValueError:
    pass
else:
    raise AssertionError('Invalid schema accepted')
assert settings_io.snapshot(prefs)==unchanged
restored=settings_io.read(config)
assert restored['general_log']==unchanged['general_log'] and restored['libraries'][1]['directory']==unchanged['libraries'][1]['directory']
assert abs(restored['libraries'][1]['unitless_scale']-unchanged['libraries'][1]['unitless_scale'])<1e-8
addon_utils.disable('sand3d_browser',default_set=False)
# Independent file loaded without importing the add-on package.
spec=importlib.util.spec_from_file_location('independent_settings',PROJECT/'sand3d_browser'/'settings_io.py')
independent=importlib.util.module_from_spec(spec)
spec.loader.exec_module(independent)
independent.import_settings(str(config))
exported=root/'independent_export.json'
independent.export_settings(str(exported))
assert independent.read(exported)==unchanged
print('POWER_IMPORTER_06_PASS',root)

