"""Integration: real USD import, source safety, generated thumbnail and asset."""
from pathlib import Path
import sys
import uuid
import hashlib
sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import bpy
from sand3d_browser.usd_io import import_model, checked_asset
from sand3d_browser.prepare_asset import prepare

root = PROJECT / 'test-artifacts' / ('assets-' + uuid.uuid4().hex)
root.mkdir(parents=True)
source = root / 'cube.usda'
source.write_text('''#usda 1.0
(
    metersPerUnit = 1
    upAxis = "Z"
)
def Cube "Cube" {
    double size = 2
}
''', encoding='utf-8')
digest = hashlib.sha256(source.read_bytes()).hexdigest()
original = set(bpy.data.objects)
frame = (bpy.context.scene.frame_start, bpy.context.scene.frame_end, bpy.context.scene.frame_current)
scale = bpy.context.scene.unit_settings.scale_length
world = bpy.context.scene.world
collection, imported = import_model(bpy.context, str(root), source.name)
assert original.issubset(set(bpy.data.objects))
assert any(o.type == 'MESH' for o in imported)
assert all(o in collection.all_objects.values() for o in imported)
assert frame == (bpy.context.scene.frame_start, bpy.context.scene.frame_end, bpy.context.scene.frame_current)
assert scale == bpy.context.scene.unit_settings.scale_length and world == bpy.context.scene.world
bad = root / 'bad.usda'
bad.write_text('#usda 1.0\n( subLayers = [@https://example.invalid/model.usda@] )\n', encoding='utf-8')
try:
    checked_asset(str(root), bad.name)
except ValueError:
    pass
else:
    raise AssertionError('External resource not rejected')
output = root / 'prepared'
prepare(str(root), source.name, str(output))
assert output.with_suffix('.png').stat().st_size > 500
assert output.with_suffix('.blend').stat().st_size > 1000
assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
bpy.ops.wm.open_mainfile(filepath=str(output.with_suffix('.blend')), load_ui=False, use_scripts=False)
assert any(c.asset_data and c.preview and c.preview.image_size[0] > 0 for c in bpy.data.collections), 'Preview not embedded in blend'
print('SAND3D_ASSETS_PASS', output)
