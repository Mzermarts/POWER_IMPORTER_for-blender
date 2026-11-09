"""Pagination beyond 500, gallery hit boxes, nested output exclusion and preparation."""
from pathlib import Path
from types import SimpleNamespace
import sys,uuid,hashlib
sys.dont_write_bytecode=True
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import bpy,addon_utils
addon_utils.enable('sand3d_browser',default_set=True)
from sand3d_browser import blender_ui as ui, gallery, actions
from sand3d_browser.catalog import Asset,scan
root=PROJECT/'test-artifacts'/('v061-'+uuid.uuid4().hex[:10])
output=root/'MZERMARTS-selections'
output.mkdir(parents=True)
(output/'generated.obj').write_text('not a source',encoding='utf-8')
model=root/'triangle.obj'
model.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n',encoding='utf-8')
digest=hashlib.sha256(model.read_bytes()).hexdigest()
items=[a for a,w in scan(str(root),excluded=(str(output),)) if a]
assert [a.relative_path for a in items]==['triangle.obj']
prefs=bpy.context.preferences.addons['sand3d_browser'].preferences
bpy.ops.sand3d.library_add()
lib=prefs.libraries[0]
lib.directory=str(root)
prefs.prepared_directory=str(output)
state=bpy.context.window_manager.sand3d_state
bpy.ops.sand3d.index()
assert len(state.results)==1
assert bpy.ops.sand3d.prepare_asset()=={'FINISHED'}
process=actions.JOB[0]
process.wait(timeout=45)
actions.refresh_job()
assert process.returncode==0
prepared=Path(actions.READY[actions.key(state.results[0])])
assert prepared.with_suffix('.png').stat().st_size>500
assert hashlib.sha256(model.read_bytes()).hexdigest()==digest
bpy.ops.sand3d.index()
assert len(state.results)==1 and state.results[0].relative_path=='triangle.obj'

# Large catalogue is synthetic in memory: no network access and no huge fixture folder.
assets=[Asset(f'model_{n:05}.obj','obj',n+10) for n in range(6001)]
ui.INDEX[lib.uid]=(lib.directory,lib.recursive,assets)
bpy.ops.sand3d.search()
assert state.total==6001 and state.page_count==7 and len(state.results)==1000
seen=[]
for page in range(1,8):
    state.page=page
    seen.extend(item.relative_path for item in state.results)
assert len(seen)==6001 and len(set(seen))==6001
assert state.results[0].relative_path=='model_06000.obj'
state.query='*0001.obj'
assert state.page==1 and state.total==1
state.query=''
state.page_size=10000
assert state.page_count==1 and len(state.results)==6001
fake=SimpleNamespace(region=SimpleNamespace(width=1200,height=800),offset=0)
fake.dimensions=lambda:gallery.S3D_OT_gallery.dimensions(fake)
state.view_mode='SMALL'
small=fake.dimensions()
assert gallery.S3D_OT_gallery.hit(fake,70,800-105)==0
assert gallery.S3D_OT_gallery.hit(fake,10,800-105)==-1
state.view_mode='LARGE'
large=fake.dimensions()
assert large[2]<small[2] and large[3]<small[3]
state.view_mode='LIST'
listed=fake.dimensions()
assert listed[2]==1 and listed[3]>small[3]
assert gallery.S3D_OT_gallery.hit(fake,70,800-138)==1
prefs.prepared_directory=str(root/'another-output')
assert not ui.INDEX and not state.results
print('POWER_IMPORTER_061_PASS',root)
