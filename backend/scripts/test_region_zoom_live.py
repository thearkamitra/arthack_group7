"""Two bounded live-provider scenarios. Never runs from unit-test discovery.
Run: PYTHONPATH=backend backend/.venv/bin/python backend/scripts/test_region_zoom_live.py --scenario center
Unity must be open on this project. No microphone is used; all dialogue is fictional.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import io
import json
import subprocess
import threading
import time
import uuid
import wave
from dataclasses import replace
from pathlib import Path

import httpx
import uvicorn
import websockets
from PIL import Image
from inner_landscape.api import create_app
from inner_landscape.config import Settings, ROOT


def session_fixture(sid):
    return dict(id=sid,clientId='demo-jamie',createdAt='2026-10-24T00:00:00Z',completedAt=None,
        status='active',goal='Explore an abstract space',preNotes='',postNotes='',exclusions='',
        before='4',after='',depth=dict(sky=0,ridge=0,water=0),region='ridge',remaining=30,
        cycle=1,pendingCycle=False,approved=False,events=[])


async def dialogue(cfg, url, token, directory, text):
    # Generate a real synthetic participant voice, then use the real conversational agent.
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post('https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL',
            params={'output_format':'pcm_16000'},headers={'xi-api-key':cfg.eleven_key},
            json={'text':text,'model_id':'eleven_flash_v2_5'})
        r.raise_for_status();pcm=r.content
    (directory/'participant.pcm').write_bytes(pcm)
    audio=bytearray();transcripts=[];sent=False
    async with websockets.connect(url,max_size=2_000_000) as ws:
        await ws.send(json.dumps({'token':token,'consent':True}))
        async def send_audio():
            for start in range(0,len(pcm),3200):
                await ws.send(json.dumps({'user_audio_chunk':base64.b64encode(pcm[start:start+3200]).decode()}))
                await asyncio.sleep(.1)
            for _ in range(20):
                await ws.send(json.dumps({'user_audio_chunk':base64.b64encode(bytes(3200)).decode()}));await asyncio.sleep(.1)
        task=None;start=time.monotonic();last=time.monotonic()
        try:
            while time.monotonic()-start<55:
                try:raw=await asyncio.wait_for(ws.recv(),timeout=1)
                except asyncio.TimeoutError:
                    if audio and time.monotonic()-last>2 and not sent:
                        task=asyncio.create_task(send_audio());sent=True
                    if sent and any(t['type']=='user_transcript' for t in transcripts) and audio and time.monotonic()-last>3:break
                    continue
                msg=json.loads(raw)
                if msg['type']=='error':raise RuntimeError('Conversational provider reported an error')
                if msg['type']=='audio':
                    audio.extend(base64.b64decode(msg['audio_event']['audio_base_64']));last=time.monotonic()
                if msg['type'] in ('user_transcript','agent_response'):transcripts.append(msg)
            if task:await task
        finally:
            if task and not task.done():task.cancel()
    if not audio or not any(t['type']=='user_transcript' for t in transcripts):
        raise RuntimeError('No verified conversational audio + participant transcript')
    with wave.open(str(directory/'guide.wav'),'wb') as out:
        out.setparams((1,2,16000,0,'NONE','not compressed'));out.writeframes(audio)
    (directory/'dialogue.json').write_text(json.dumps(transcripts,indent=2))
    return {'tts_bytes':len(pcm),'guide_bytes':len(audio),'transcript_events':len(transcripts)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['center','upper-left'],required=True)
    parser.add_argument('--reuse-media',type=Path);parser.add_argument('--reuse-dialogue',type=Path);parser.add_argument('--port',type=int,default=4174);args=parser.parse_args()
    cfg=Settings.load()
    if not cfg.fal_key or not cfg.eleven_key or not cfg.agent_id:raise SystemExit('Configure backend provider credentials first')
    for command in ('ffmpeg','ffprobe'):
        subprocess.run([command,'-version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    directory=ROOT/'work/region_zoom_tests'/f'{time.time_ns()}-{args.scenario}';directory.mkdir(parents=True)
    # Isolated coordinator DB; never modify an existing user workspace/run.
    sandbox=directory/'coordinator';sandbox.mkdir();(sandbox/'frontend').symlink_to(ROOT/'frontend',target_is_directory=True)
    cfg=replace(cfg,root=sandbox,paid_enabled=True)
    app=create_app(cfg);server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    base=f'http://127.0.0.1:{args.port}';sid='synthetic-'+uuid.uuid4().hex
    manifest=dict(scenario=args.scenario,status='running',mode='LIVE',directory=str(directory),session_id=sid,
        inputs={'source':str(ROOT/'Assets/Images/ideal_abstract.jpeg')},commands=['test_region_zoom_live.py --scenario '+args.scenario])
    def save(): (directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
    save()
    try:
        with httpx.Client(base_url=base,timeout=30) as client:
            deadline=time.monotonic()+15
            while not server.started and time.monotonic()<deadline:time.sleep(.1)
            if not server.started:raise RuntimeError("Isolated coordinator failed to start; port may be occupied")
            client.get('/').raise_for_status()
            def post(path,data):
                r=client.post('/api/sessions/'+sid+path,json=data);r.raise_for_status();return r.json()
            snapshot=client.get('/api/workspace').json()
            client.put('/api/workspace',json={'revision':snapshot['revision'],'workspace':dict(version=1,notes={},sessions=[session_fixture(sid)])}).raise_for_status()
            buf=io.BytesIO();Image.open(ROOT/'Assets/Images/ideal_abstract.jpeg').convert('RGB').save(buf,format='PNG');raw=buf.getvalue()
            post('/scene',{'image':'data:image/png;base64,'+base64.b64encode(raw).decode()})
            code=post('/pair',{})['code'];token=client.post('/api/pair',json={'code':code}).json()['token']
            text='I notice the pink floating oval and blue light in the upper left. I would like to explore that textured space gently.' if args.scenario=='upper-left' else 'I notice the luminous flowing forms near the center. I would like to explore their soft light gently.'
            if args.reuse_dialogue:
                import shutil
                for name in ('guide.wav','dialogue.json','participant.pcm'):shutil.copy2(args.reuse_dialogue/name,directory/name)
                manifest['voice']={'live_evidence_from':str(args.reuse_dialogue),'reused_for_unity_retry':True}
            else:
                manifest['voice']=asyncio.run(dialogue(cfg,base.replace('http','ws')+'/api/sessions/'+sid+'/voice',token,directory,text))
            turns=json.loads((directory/'dialogue.json').read_text())
            users=[t.get('user_transcription_event',t.get('user_transcript_event',{})).get('user_transcript','') for t in turns if t['type']=='user_transcript']
            guides=[t.get('agent_response_event',{}).get('agent_response','') for t in turns if t['type']=='agent_response']
            text=('Participant: '+users[-1][:400]+' Guide: '+guides[-1][:160])[:600]
            manifest['approved_excerpt']=text
            save()
            # A fresh single-use pair code belongs only to Unity.
            code=post('/pair',{})['code']
            pending=ROOT/'work/region_zoom_tests/unity-request.json'
            if pending.exists():raise RuntimeError('Another Unity scenario is pending')
            pending.write_text(json.dumps(dict(server=base,code=code,audio=str(directory/'guide.wav'),directory=str(directory),scenario=args.scenario)))
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                s=client.get('/api/sessions/'+sid).json()
                if s.get('spatialDecision'):break
                time.sleep(.5)
            else:raise RuntimeError('Unity did not report a spatial decision within 90s; open Unity and exit prior Play Mode')
            d=s['spatialDecision'];manifest['decision']=d;assert d['cell']==(0 if args.scenario=='upper-left' else 4)
            assert abs(d['percentages'][d['cell']]-(70 if args.scenario=='upper-left' else 80))<3
            if args.scenario=='upper-left':
                assert abs(d['x']-.2)<.01 and abs(d['y']-.08)<.01 and d['crop']==[0,0,.5,.5]
            def ready(job):
                limit=time.monotonic()+660
                while time.monotonic()<limit:
                    jobs=client.get('/api/sessions/'+sid+'/media').json();j=next(j for j in jobs if j['id']==job['id'])
                    if j['status']=='ready':return j
                    if j['status'] in ('failed','unknown','cancelled'):raise RuntimeError('Provider job '+j['status']+'; reconcile '+j['id'])
                    time.sleep(2)
                raise RuntimeError('Bounded job wait expired; no resubmission')
            if args.reuse_media:
                import shutil
                previous=json.loads((args.reuse_media/'manifest.json').read_text())
                for key in ('image_job','video_job'):
                    job=previous[key].copy();job['session_id']=sid;job['entry']=d;job['cycle']=1
                    source=args.reuse_media/'coordinator/work/coordinator/media'/job['id']
                    dest=cfg.work/'media'/job['id'];shutil.copytree(source,dest)
                    app.state.media.persist(job);manifest[key]=job
                image=manifest['image_job'];video=manifest['video_job']
                manifest['mode']='REPLAY';manifest['live_media_from']=str(args.reuse_media);save()
            else:
                image=ready(post('/region-entry',{'excerpt':text}));manifest['image_job']=image;save()
                # Synthetic test therapist approves the fictional start image and video.
                video=ready(post('/region-entry',{'excerpt':text,'parent_job':image['id']}));manifest['video_job']=video;save()
            assert abs(video['validation']['duration_seconds']-5)<.2
            if not args.reuse_media:assert max(video['final_resolution'])>=2560
            from PIL import ImageChops, ImageStat
            media_dir=cfg.work/'media'
            with Image.open(media_dir/image['id']/image['output_path']) as still, Image.open(media_dir/video['id']/'first.png') as first:
                diff=ImageChops.difference(still.convert('RGB').resize(first.size),first.convert('RGB'))
                manifest['first_frame_mean_absolute_difference']=sum(ImageStat.Stat(diff).mean)/3/255
            save()
            post('/media/apply',{'job_id':video['id'],'continuity_confirmed':True})
            deadline=time.monotonic()+60
            pause_checked=False
            while time.monotonic()<deadline:
                s=client.get('/api/sessions/'+sid).json()
                statefile=directory/'unity-states.jsonl'
                if not pause_checked and statefile.exists() and '"state":"PlayVideo"' in statefile.read_text():
                    post('/commands',{'command_id':uuid.uuid4().hex,'command':'pause','payload':{}})
                    time.sleep(1.4)
                    poses=[json.loads(line) for line in (directory/'pose-samples.jsonl').read_text().splitlines()]
                    held=[p for p in poses if p['hold']]
                    assert len(held)>=2 and abs(held[-1]['video_time']-held[0]['video_time'])<.15
                    assert all(abs(held[-1][k]-held[0][k])<.001 for k in ('x','y','z'))
                    post('/commands',{'command_id':uuid.uuid4().hex,'command':'resume','payload':{}})
                    pause_checked=True;manifest['remote_pause_verified']=True;save()
                if s['cycle']==2 and s.get('source_hash')==video['frame_hashes']['final.png']:break
                time.sleep(.5)
            else:raise RuntimeError('Unity did not complete/acknowledge the transition')
            assert (directory/'unity-complete.json').exists()
            assert json.loads((directory/'cancel-check.json').read_text())['no_completion']
            fit=json.loads((directory/'fit.json').read_text())
            assert 0 <= fit['min_x'] <= fit['max_x'] <= 1 and 0 <= fit['min_y'] <= fit['max_y'] <= 1
            manifest['fit']=fit
            states=[json.loads(line)['state'] for line in (directory/'unity-states.jsonl').read_text().splitlines()]
            expected=['PullBack','SwapStartFrame','PlayVideo','Approach','Exploring']
            assert [state for state in states if state in expected][:5]==expected
            subprocess.run(['ffmpeg','-v','error','-y','-framerate','10','-i',str(directory/'frames/frame-%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(directory/'unity-transition.mp4')],check=True,timeout=30)
            manifest['recording']=str(directory/'unity-transition.mp4')
            manifest['status']='passed';manifest['next_source_hash']=s['source_hash'];save()
    except Exception as exc:
        manifest['status']='failed';manifest['error']=type(exc).__name__+': '+str(exc).split(' for url:')[0];save()
        raise
    finally:
        server.should_exit=True;thread.join(timeout=5)
        print('Evidence:',directory,'status:',manifest['status'])

if __name__=='__main__':main()
