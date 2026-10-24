"""Bounded local frontend-control/Unity integration; no provider calls or microphone."""
import base64
import io
import json
import os
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path
import httpx
import uvicorn
from PIL import Image
from inner_landscape.api import create_app
from inner_landscape.config import Settings,ROOT
from test_region_zoom_live import session_fixture

run=ROOT/'work/browser_demo'/str(time.time_ns());run.mkdir(parents=True)
sandbox=run/'sandbox';sandbox.mkdir();(sandbox/'frontend').symlink_to(ROOT/'frontend',target_is_directory=True)
app=create_app(replace(Settings(),root=sandbox))
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=4175,log_level='warning',access_log=False))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
manifest={'status':'running','mode':'LOCAL_NO_PROVIDERS','directory':str(run)}
process=None
try:
    with httpx.Client(base_url='http://127.0.0.1:4175',timeout=5) as client:
        until=time.monotonic()+15
        while not server.started and time.monotonic()<until:time.sleep(.1)
        client.get('/').raise_for_status();snap=client.get('/api/workspace').json()
        sid='browser-demo-check';prefix='/api/sessions/'+sid
        client.put('/api/workspace',json={'revision':snap['revision'],'workspace':{'version':1,'notes':{},'sessions':[session_fixture(sid)]}}).raise_for_status()
        output=io.BytesIO();Image.open(ROOT/'Assets/Images/ideal_abstract.jpeg').convert('RGB').save(output,format='PNG')
        client.post(prefix+'/scene',json={'image':'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()}).raise_for_status()
        client.post(prefix+'/demo/start').raise_for_status()
        environment=os.environ.copy();environment['INNER_LANDSCAPE_DEMO_URL']='http://127.0.0.1:4175'
        process=subprocess.Popen(['/Applications/Unity/Hub/Editor/6000.6.7f1/Unity.app/Contents/MacOS/Unity','-batchmode','-projectPath',str(ROOT),'-executeMethod','InnerLandscape.Editor.BrowserDemoLauncher.Prepare','-logFile',str(run/'unity.log')],env=environment)
        marker=ROOT/'work/browser_demo/editor-start.json';marker.write_text('{"start":true}')
        until=time.monotonic()+75
        while time.monotonic()<until:
            state=client.get(prefix).json()['demo']
            if state['connected'] and state['frame_ready']:break
            if process.poll() is not None:raise RuntimeError('Unity exited; inspect its compile/startup log')
            time.sleep(.3)
        else:raise RuntimeError('Unity did not auto-pair and return preview')
        def frame(name):
            r=client.get(prefix+'/demo/frame');r.raise_for_status();(run/name).write_bytes(r.content);return r.content
        before=frame('center.jpg')
        # Browser controls are authoritative; measure attention during emulated audible guide playback.
        client.post(prefix+'/demo/speech',json={'speaking':True,'window_id':'browser-turn','sequence':1}).raise_for_status()
        for direction in ['left']*4+['up']*2:
            client.post(prefix+'/demo/input',json={'action':direction}).raise_for_status()
        for sequence in range(2,12):
            client.post(prefix+'/demo/speech',json={'speaking':True,'window_id':'browser-turn','sequence':sequence}).raise_for_status();time.sleep(.2)
        after=frame('left-up.jpg');assert after!=before
        client.post(prefix+'/demo/speech',json={'speaking':False,'window_id':'browser-turn','sequence':12}).raise_for_status()
        client.post(prefix+'/demo/input',json={'action':'freeze'}).raise_for_status()
        until=time.monotonic()+10
        while time.monotonic()<until:
            session=client.get(prefix).json()
            if session.get('spatialDecision'):break
            time.sleep(.2)
        else:raise RuntimeError('Frontend confirmation did not freeze Unity attention')
        assert not session['spatialDecision'].get('manual',False)
        assert session['spatialDecision']['speaking_seconds']>=.5
        manifest.update(status='passed',decision=session['spatialDecision'],camera=session['demo'],frame_changed=True)
except Exception as exc:
    manifest.update(status='failed',error=str(exc));raise
finally:
    if process:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill()
    server.should_exit=True;thread.join(timeout=5)
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2));print('Browser control evidence:',run,manifest['status'])
