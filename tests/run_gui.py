"""Run a GUI integration test with a fresh Blender profile; retain diagnostics."""
import argparse,os,subprocess,uuid
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('script')
parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe')
args=parser.parse_args()
project=Path(__file__).resolve().parents[1]
profile=project/'test-artifacts'/('gui-'+uuid.uuid4().hex[:10])
env=os.environ.copy()
for key,tail in {'BLENDER_USER_RESOURCES':'','BLENDER_USER_CONFIG':'config','BLENDER_USER_SCRIPTS':'scripts','BLENDER_USER_EXTENSIONS':'extensions','BLENDER_USER_DATAFILES':'datafiles'}.items():
    folder=profile/tail
    folder.mkdir(parents=True,exist_ok=True)
    env[key]=str(folder)
env['MZERMARTS_TEST_OUTPUT']=str(profile)
with (profile/'blender.log').open('w',encoding='utf-8') as log:
    subprocess.run([args.blender,'--background','--factory-startup','--disable-autoexec','--python-expr','import bpy; bpy.context.preferences.view.show_splash=False; bpy.ops.wm.save_userpref()'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    process=subprocess.Popen([args.blender,'--disable-autoexec','--python',str(project/'tests'/args.script)],env=env,stdout=log,stderr=subprocess.STDOUT)
    print('ISOLATED_GUI_PID',process.pid,'OUTPUT',profile,flush=True)
    try:
        process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        process.terminate()
        raise
report=profile/'result.json'
print(report.read_text(encoding='utf-8') if report.is_file() else (profile/'blender.log').read_text(encoding='utf-8'),flush=True)
if not report.is_file() or '"PASS"' not in report.read_text(encoding='utf-8'):
    raise SystemExit(1)
