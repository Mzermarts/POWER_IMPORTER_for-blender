"""Real Blender OBJ/STL/glTF imports, textures, scale, cache and previews."""
from pathlib import Path
import sys
import uuid
import struct
import json
import hashlib
sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import bpy
import addon_utils
addon_utils.enable('sand3d_browser', default_set=True)
from sand3d_browser.model_io import import_model, dependencies
from sand3d_browser.catalog import scan
from sand3d_browser import actions

root = PROJECT / 'test-artifacts' / ('formats-' + uuid.uuid4().hex)
source = root / 'source'
output = root / 'prepared'
source.mkdir(parents=True)
output.mkdir()
image = bpy.data.images.new('fixture_texture', width=2, height=2)
image.pixels = [0.8, 0.2, 0.1, 1.0] * 4
image.filepath_raw = str(source / 'texture.png')
image.file_format = 'PNG'
image.save()
(source / 'triangle.obj').write_text('mtllib triangle.mtl\no Triangle\nv 0 0 0\nv 2 0 0\nv 0 2 0\nvt 0 0\nvt 1 0\nvt 0 1\nusemtl Red\nf 1/1 2/2 3/3\n', encoding='utf-8')
(source / 'triangle.mtl').write_text('newmtl Red\nKd 0.8 0.2 0.1\nmap_Kd texture.png\n', encoding='utf-8')
ascii_stl = 'solid triangle\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 2 0 0\nvertex 0 2 0\nendloop\nendfacet\nendsolid triangle\n'
(source / 'ascii.stl').write_text(ascii_stl, encoding='ascii')
(source / 'binary.stl').write_bytes(b'fixture'.ljust(80, b'\0') + struct.pack('<I', 1)
    + struct.pack('<12fH', 0,0,1, 0,0,0, 2,0,0, 0,2,0, 0))
(source / 'warp.cpp.obj').write_bytes(b'not a Wavefront model')
(source / 'inventory.3mf').write_bytes(b'not imported in this version')
cube = bpy.data.objects['Cube']
material = bpy.data.materials.new('glTF textured fixture')
material.use_nodes = True
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.image = image
material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
cube.data.materials.clear()
cube.data.materials.append(material)
bpy.ops.export_scene.gltf(filepath=str(source / 'model.glb'), export_format='GLB', use_selection=True)
bpy.ops.export_scene.gltf(filepath=str(source / 'model.gltf'), export_format='GLTF_SEPARATE', use_selection=True)

hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
inventory = [a.relative_path for a,w in scan(str(source), False) if a]
assert 'warp.cpp.obj' not in inventory and 'triangle.obj' in inventory and 'inventory.3mf' in inventory
assert len(dependencies(str(source), 'triangle.obj')[1]) == 3
assert len(dependencies(str(source), 'model.gltf')[1]) >= 3
originals = {o: o.matrix_world.copy() for o in bpy.data.objects}
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 12, 89
scene.frame_set(23)
scene.render.fps = 30
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.01
scale_before = scene.unit_settings.scale_length
camera, world = scene.camera, scene.world
for name in ('triangle.obj', 'ascii.stl', 'binary.stl', 'model.glb', 'model.gltf'):
    previous_images = set(bpy.data.images)
    collection, objects = import_model(bpy.context, str(source), name)
    assert any(o.type == 'MESH' and len(o.data.polygons) for o in objects), name
    assert all(o in collection.all_objects.values() for o in objects), name
    assert all(o in bpy.data.objects.values() and o.matrix_world == matrix for o,matrix in originals.items())
    assert (scene.frame_start, scene.frame_end, scene.frame_current, scene.render.fps) == (12, 89, 23, 30)
    assert scene.unit_settings.scale_length == scale_before and scene.unit_settings.system == 'METRIC'
    assert scene.camera == camera and scene.world == world
    if name == 'triangle.obj' or name.startswith('model.'):
        assert any(o.type == 'MESH' and len(o.data.materials) for o in objects)
        textures = [n.image for o in objects if o.type == 'MESH' for m in o.data.materials if m and m.use_nodes
                    for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        assert textures and all(img.packed_file for img in textures if img not in previous_images), name
    print('FORMAT_IMPORT_PASS', name)
_, scaled = import_model(bpy.context, str(source), 'binary.stl', 0.001)
bpy.context.view_layer.update()
assert abs(scaled[0].dimensions.x - 0.002) < 0.000001

# Reject URI resources before invoking the native importer.
(source / 'remote.gltf').write_text(json.dumps({'asset': {'version': '2.0'}, 'buffers': [{'uri': 'https://example.invalid/x.bin'}]}), encoding='utf-8')
(source / 'outside.obj').write_text('v 0 0 0\nmtllib ../outside.mtl\n', encoding='utf-8')
for bad in ('remote.gltf', 'outside.obj', 'warp.cpp.obj', 'inventory.3mf'):
    before = set(bpy.data.objects)
    try:
        dependencies(str(source), bad)
    except ValueError:
        pass
    else:
        raise AssertionError('Unsupported/unsafe file accepted: ' + bad)
    assert before == set(bpy.data.objects)

# Exercise the actual async operators and native asset-library registration.
prefs = bpy.context.preferences.addons['sand3d_browser'].preferences
bpy.ops.sand3d.library_add()
prefs.libraries[0].directory = str(source)
prefs.prepared_directory = str(output)
bpy.ops.sand3d.index()
state = bpy.context.window_manager.sand3d_state
prepared_paths = []
for name in ('triangle.obj', 'binary.stl', 'model.glb', 'model.gltf'):
    state.query = name
    state.format_filter = 'ALL'
    bpy.ops.sand3d.search()
    assert len(state.results) == 1
    assert bpy.ops.sand3d.prepare_asset() == {'FINISHED'}
    process = actions.JOB[0]
    process.wait(timeout=45)
    actions.refresh_job()
    assert process.returncode == 0, name
    item = state.results[0]
    prepared = Path(actions.READY[actions.key(item)])
    assert prepared.with_suffix('.png').stat().st_size > 500
    assert prepared.with_suffix('.blend').stat().st_size > 1000
    prepared_paths.append(prepared)
    assert bpy.ops.sand3d.prepare_asset() == {'FINISHED'} and actions.JOB is None
    print('FORMAT_PREVIEW_PASS', name, prepared)
state.query = ''
state.format_filter = 'STL'
bpy.ops.sand3d.search()
assert len(state.results) == 2 and all(i.format == 'stl' for i in state.results)
assert all(hashlib.sha256((source/name).read_bytes()).hexdigest() == digest for name,digest in hashes.items())
addon_utils.disable('sand3d_browser', default_set=True)
for prepared in prepared_paths:
    bpy.ops.wm.open_mainfile(filepath=str(prepared.with_suffix('.blend')), load_ui=False, use_scripts=False)
    assets = [c for c in bpy.data.collections if c.asset_data]
    assert assets and all(c.preview and c.preview.image_size[0] > 0 for c in assets)
    textures = [n.image for c in assets for o in c.all_objects if o.type == 'MESH' for m in o.data.materials if m and m.use_nodes
                for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    assert all(image.packed_file for image in textures), prepared
print('SAND3D_MULTIFORMAT_PASS', root)
