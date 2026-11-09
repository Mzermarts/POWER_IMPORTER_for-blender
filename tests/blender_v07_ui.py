"""Real workspace/window hosting and scene-safe model/image actions."""
import sys,os,json,traceback
from pathlib import Path
sys.dont_write_bytecode=True
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import bpy,addon_utils
addon_utils.enable('sand3d_browser',default_set=True)
from sand3d_browser import browser_windows as host, gallery
root=Path(os.environ['MZERMARTS_TEST_OUTPUT'])
source=root/'sources'
source.mkdir()
(source/'triangle.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n',encoding='utf-8')
image=bpy.data.images.new('Test color',width=64,height=32)
image.pixels=[0.2,0.5,0.8,1]*(64*32)
image.filepath_raw=str(source/'color.png')
image.file_format='PNG'
image.save()
prefs=bpy.context.preferences.addons['sand3d_browser'].preferences
bpy.ops.sand3d.library_add()
prefs.libraries[0].directory=str(source)
bpy.ops.sand3d.index()
state=bpy.context.window_manager.sand3d_state
origin=bpy.context.window_manager.windows[0]
scene_a=origin.scene
scene_b=bpy.data.scenes.new('Browser scene not destination')
cube=bpy.data.objects['Cube']
stage=0
report={'version':bpy.app.version_string,'checks':[]}
browser=None
old_windows=None

def context(window):
    area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
    region=next(r for r in area.regions if r.type=='WINDOW')
    return bpy.context.temp_override(window=window,area=area,region=region)

def finish():
    (root/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    bpy.ops.wm.quit_blender()

def step():
    global stage,browser,old_windows
    try:
        if stage==0:
            with context(origin):
                assert bpy.ops.sand3d.open_browser(mode='WORKSPACE')=={'FINISHED'}
            stage=1
            return 0.8
        if stage==1:
            assert origin.workspace.get(host.MARKER) and origin.scene==scene_a
            assert state.destination_scene==scene_a
            report['checks'].append('workspace created; source scene preserved')
            old_windows=set(bpy.context.window_manager.windows)
            with context(origin):
                assert bpy.ops.sand3d.open_browser(mode='WINDOW')=={'FINISHED'}
            stage=2
            return 0.8
        if stage==2:
            browser=next(w for w in bpy.context.window_manager.windows if w not in old_windows)
            browser.scene=scene_b
            state.query='*.obj'
            before=set(scene_a.objects)
            with context(browser):
                assert host.is_browser(bpy.context)
                assert bpy.ops.sand3d.import_selected()=={'FINISHED'}
            assert set(scene_a.objects)>before and len(scene_b.objects)==0
            report['checks'].append('model import goes to source scene even with different browser scene')
            state.query='*.png'
            origin.view_layer.objects.active=cube
            previous=len(cube.data.materials)
            with context(browser):
                assert bpy.ops.sand3d.image_action(action='APPLY')=={'FINISHED'}
            assert len(cube.data.materials)==previous+1 and len(scene_b.objects)==0
            report['checks'].append('image material applied to source active mesh')
            stage=3
            return 0.8
        if stage==3:
            origin.scene=scene_b
            state.query='*.obj'
            count=len(bpy.data.objects)
            with context(browser):
                try:
                    bpy.ops.sand3d.import_selected()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Changed destination was accepted')
            assert len(bpy.data.objects)==count
            origin.scene=scene_a
            report['checks'].append('changed destination blocks import before mutation')
            stage=4
            return 0.8
        if stage==4:
            with context(browser):
                area=bpy.context.area
                width=gallery.visible_width(next(r for r in area.regions if r.type=='WINDOW'),area)
                ui=next(r for r in area.regions if r.type=='UI')
                assert width<=ui.x and ui.width>1
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP',iterations=1)
                bpy.ops.screen.screenshot(filepath=str(root/'browser.png'))
            report['checks'].append('gallery reserves sidebar width; screenshot captured')
            workspaces=len([w for w in bpy.data.workspaces if w.get(host.MARKER)])
            with context(origin):
                assert bpy.ops.sand3d.open_browser(mode='WORKSPACE')=={'FINISHED'}
            assert len([w for w in bpy.data.workspaces if w.get(host.MARKER)])==workspaces==1
            report['checks'].append('workspace reused without duplication')
            stage=5
            return 0.8
        if stage==5:
            if gallery.ACTIVE:
                gallery.ACTIVE.finish(bpy.context)
            with context(origin):
                bpy.ops.wm.window_close()
            stage=6
            return 0.8
        if stage==6:
            count=len(bpy.data.objects)
            with context(browser):
                try:
                    bpy.ops.sand3d.import_selected()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Closed destination was accepted')
            assert len(bpy.data.objects)==count
            report['checks'].append('closed destination blocks import before mutation')
            addon_utils.disable('sand3d_browser',default_set=False)
            report['checks'].append('unregister with browser windows open')
            report['result']='PASS'
            finish()
    except Exception:
        report['result']='FAIL'
        report['error']=traceback.format_exc()
        finish()
    return None

bpy.context.preferences.view.show_splash=False
bpy.app.timers.register(step,first_interval=2)
