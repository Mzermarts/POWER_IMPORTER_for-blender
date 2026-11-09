"""Run only in an isolated factory-startup Blender process; never save prefs."""
from pathlib import Path
import hashlib
import sys
import uuid
import bpy
import addon_utils

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.dont_write_bytecode = True
fixture = PROJECT / "test-artifacts" / uuid.uuid4().hex
fixture.mkdir(parents=True)
(fixture / "sub").mkdir()
(fixture / "bracket.usda").write_text('#usda 1.0\n', encoding="utf-8")
(fixture / "sub" / "gear.stl").write_text('solid test\nendsolid test\n', encoding="utf-8")
(fixture / "do_not_execute.py").write_text('raise RuntimeError("NEVER RUN")\n', encoding="utf-8")
before = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in fixture.rglob("*") if p.is_file()}
scene_before = tuple(bpy.data.objects)
addon_utils.enable("sand3d_browser", default_set=True)
assert addon_utils.check("sand3d_browser")[1], "Add-on registration failed"
from sand3d_browser import blender_ui as ui
from sand3d_browser.catalog import local_root, scan
from unittest.mock import patch
# Validate Windows path handling without contacting any real server/share.
for root in (r'Z:\Production\CAD', r'\\serveur-test\production\CAD'):
    with patch('sand3d_browser.catalog.is_link', return_value=False) as link_check, \
         patch.object(Path, 'resolve', return_value=Path(root)), \
         patch.object(Path, 'is_dir', return_value=True):
        assert local_root(root) == Path(root)
        link_check.assert_called_once_with(Path(root))
prefs = bpy.context.preferences.addons["sand3d_browser"].preferences
assert not prefs.libraries
assert bpy.ops.sand3d.library_add() == {'FINISHED'}
first = prefs.libraries[0]
first.directory = str(fixture)
assert bpy.ops.sand3d.index() == {'FINISHED'}
state = bpy.context.window_manager.sand3d_state
assert len(state.results) == 2, list(r.relative_path for r in state.results)
state.query = "gear"
bpy.ops.sand3d.search()
assert len(state.results) == 1 and state.results[0].format == "stl"
first.recursive = False
assert not state.results and first.uid not in ui.INDEX
state.query = ""
bpy.ops.sand3d.index()
assert len(state.results) == 1
first.enabled = False
bpy.ops.sand3d.search()
assert not state.results
first.enabled = True
first.recursive = True
bpy.ops.sand3d.library_add()
prefs.libraries[1].directory = str(fixture)
bpy.ops.sand3d.index()
assert len(state.results) == 2, "Duplicate root indexed twice"
bpy.ops.sand3d.library_remove()
assert len(prefs.libraries) == 1 and (fixture / "bracket.usda").exists()
first = prefs.libraries[0]
first.directory = str(fixture / "absent")
bpy.ops.sand3d.index()
assert not state.results and not ui.RUNNING
for bad in ("", "relative/path"):
    try:
        local_root(bad)
    except (ValueError, OSError):
        pass
    else:
        raise AssertionError(f"Unsafe path accepted: {bad}")
assert len([a for a, _ in scan(str(fixture), False) if a]) == 1
assert tuple(bpy.data.objects) == scene_before
after = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in fixture.rglob("*") if p.is_file()}
assert before == after, "Source fixture changed"
addon_utils.disable("sand3d_browser", default_set=True)
assert not hasattr(bpy.types.WindowManager, "sand3d_state")
addon_utils.enable("sand3d_browser", default_set=True)
addon_utils.disable("sand3d_browser", default_set=True)
print("SAND3D_TEST_PASS", bpy.app.version_string,
      "registration, library CRUD, recursion, duplicates, search, invalid paths, source integrity, unregister")
