"""Texture recovery and the two user-configured journals, without production IO."""
from pathlib import Path
import sys
import uuid
import json
import hashlib
import struct
sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import bpy
import addon_utils
addon_utils.enable('sand3d_browser', default_set=True)
from sand3d_browser import actions, operation_log
from sand3d_browser.model_io import dependencies, import_model
from sand3d_browser.texture_recovery import MissingTextures

root = PROJECT / 'test-artifacts' / ('recovery-' + uuid.uuid4().hex)
source, output, chosen = root / 'source', root / 'prepared', root / 'user_selected'
for folder in (source, output, chosen):
    folder.mkdir(parents=True)
image = bpy.data.images.new('replacement fixture', width=2, height=2)
image.pixels = [0.2, 0.7, 0.1, 1] * 4
image.filepath_raw = str(chosen / 'chosen texture.png')
image.file_format = 'PNG'
image.save()
(source / 'missing.obj').write_text('mtllib missing.mtl\no Triangle\nv 0 0 0\nv 2 0 0\nv 0 2 0\nvt 0 0\nvt 1 0\nvt 0 1\nusemtl Recovery\nf 1/1 2/2 3/3\n', encoding='utf-8')
(source / 'missing.mtl').write_text('newmtl Recovery\nKd 0.8 0.6 0.3\nmap_Kd C:/old/DAZ/temp/HexagonMaps/Final Fight Texture.jpg\n', encoding='utf-8')
hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}
prefs = bpy.context.preferences.addons['sand3d_browser'].preferences
prefs.general_log, prefs.error_log = str(root / 'general.jsonl'), str(root / 'errors.jsonl')
assert bpy.ops.sand3d.test_logs() == {'FINISHED'}
assert Path(prefs.error_log).read_text() == ''
bpy.ops.sand3d.library_add()
prefs.libraries[0].directory = str(source)
prefs.prepared_directory = str(output)
bpy.ops.sand3d.index()
state = bpy.context.window_manager.sand3d_state
state.query = 'missing.obj'
bpy.ops.sand3d.search()
before = set(bpy.data.objects)
assert bpy.ops.sand3d.import_selected() == {'FINISHED'}
assert before == set(bpy.data.objects), 'Geometry imported before recovery choice'
assert actions.PENDING and len(state.texture_issues) == 1
assert bpy.ops.sand3d.choose_texture(issue_index=0, filepath=str(chosen / 'chosen texture.png')) == {'FINISHED'}
assert bpy.ops.sand3d.resume_textures(omit=False) == {'FINISHED'}
assert not actions.PENDING and set(bpy.data.objects) > before

# A fresh attempt can explicitly omit textures while preserving Kd materials.
bpy.ops.sand3d.import_selected()
before = set(bpy.data.objects)
assert bpy.ops.sand3d.resume_textures(omit=True) == {'FINISHED'}
new_objects = set(bpy.data.objects) - before
assert new_objects
assert not any(n.type == 'TEX_IMAGE' for o in new_objects if o.type == 'MESH' for mat in o.data.materials if mat and mat.node_tree for n in mat.node_tree.nodes)

# Same user choice works in the isolated preparation subprocess.
assert bpy.ops.sand3d.prepare_asset() == {'FINISHED'} and actions.PENDING
bpy.ops.sand3d.choose_texture(issue_index=0, filepath=str(chosen / 'chosen texture.png'))
assert bpy.ops.sand3d.resume_textures(omit=False) == {'FINISHED'}
process = actions.JOB[0]
process.wait(timeout=45)
actions.refresh_job()
assert process.returncode == 0 and actions.key(state.results[0]) in actions.READY

# glTF image recovery: missing images are recoverable; missing buffers are not.
cube = bpy.data.objects['Cube']
for obj in bpy.context.selected_objects:
    obj.select_set(False)
cube.select_set(True)
bpy.context.view_layer.objects.active = cube
material = bpy.data.materials.new('recovery glTF fixture')
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.image = image
material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
cube.data.materials.clear()
cube.data.materials.append(material)
bpy.ops.export_scene.gltf(filepath=str(source / 'recover.gltf'), export_format='GLTF_SEPARATE', use_selection=True)
document = json.loads((source / 'recover.gltf').read_text())
document['images'][0]['uri'] = 'lost_texture.png'
(source / 'recover.gltf').write_text(json.dumps(document), encoding='utf-8')
try:
    dependencies(str(source), 'recover.gltf')
except MissingTextures as exc:
    mapping = {exc.issues[0]['key']: str(chosen / 'chosen texture.png')}
else:
    raise AssertionError('glTF missing texture not reported')
assert import_model(bpy.context, str(source), 'recover.gltf', omit=True)[1]
assert import_model(bpy.context, str(source), 'recover.gltf', replacements=mapping)[1]
payload = json.dumps(document).encode('utf-8')
payload += b' ' * (-len(payload) % 4)
(source / 'recover.glb').write_bytes(struct.pack('<4sIIII', b'glTF', 2, 20 + len(payload), len(payload), 0x4E4F534A) + payload)
try:
    dependencies(str(source), 'recover.glb')
except MissingTextures as exc:
    glb_mapping = {exc.issues[0]['key']: str(chosen / 'chosen texture.png')}
else:
    raise AssertionError('GLB missing external texture not reported')
assert import_model(bpy.context, str(source), 'recover.glb', omit=True)[1]
assert import_model(bpy.context, str(source), 'recover.glb', replacements=glb_mapping)[1]

# USD texture recovery across a sublayer, without composing unresolved sources.
from pxr import Usd, UsdGeom, UsdShade, Sdf
stage = Usd.Stage.CreateNew(str(source / 'textured.usda'))
cube_usd = UsdGeom.Cube.Define(stage, '/Cube')
mat_usd = UsdShade.Material.Define(stage, '/Material')
shader = UsdShade.Shader.Define(stage, '/Material/Surface')
shader.CreateIdAttr('UsdPreviewSurface')
tex = UsdShade.Shader.Define(stage, '/Material/Texture')
tex.CreateIdAttr('UsdUVTexture')
tex.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('lost_usd_texture.png'))
tex.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(), 'rgb')
mat_usd.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
UsdShade.MaterialBindingAPI.Apply(cube_usd.GetPrim()).Bind(mat_usd)
stage.GetRootLayer().Save()
scene_layer = Sdf.Layer.CreateNew(str(source / 'usd_scene.usda'))
scene_layer.subLayerPaths.append('textured.usda')
scene_layer.Save()
try:
    dependencies(str(source), 'usd_scene.usda')
except MissingTextures as exc:
    usd_mapping = {exc.issues[0]['key']: str(chosen / 'chosen texture.png')}
else:
    raise AssertionError('USD missing texture not reported')
assert import_model(bpy.context, str(source), 'usd_scene.usda', omit=True)[1]
assert import_model(bpy.context, str(source), 'usd_scene.usda', replacements=usd_mapping)[1]

# Preparation path failure is explicit and recorded in errors-only journal.
prefs.prepared_directory = ''
bpy.ops.sand3d.index()
state.query='missing.obj'
bpy.ops.sand3d.search()
try:
    bpy.ops.sand3d.prepare_asset()
except RuntimeError as exc:
    assert 'Dossier des assets préparés' in str(exc)
general = [json.loads(line) for line in Path(prefs.general_log).read_text(encoding='utf-8').splitlines()]
errors = [json.loads(line) for line in Path(prefs.error_log).read_text(encoding='utf-8').splitlines()]
assert general and errors and all(row['level'] == 'ERROR' for row in errors)
assert any(row['event'] == 'texture_selected_by_user' for row in general)
assert any(row['event'] == 'import_finished' for row in general)
assert any(row['event'] == 'missing_textures' and row.get('traceback') for row in errors)
assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p,digest in hashes.items())
# A logging failure must not fail an otherwise valid operation.
prefs.general_log = str(root / 'absent' / 'general.log')
assert bpy.ops.sand3d.library_add() == {'FINISHED'}
assert operation_log.LAST_ERROR
addon_utils.disable('sand3d_browser', default_set=True)
print('SAND3D_RECOVERY_LOGS_PASS', root)
