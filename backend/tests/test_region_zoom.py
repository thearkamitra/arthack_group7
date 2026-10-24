import copy
import unittest
from inner_landscape.region_zoom import decision, crop_box, visual_brief
from inner_landscape.domain import command, participant_view
from test_service import fixture


def attention():
    return dict(cycle=1,source_hash='a'*64,input_mode='scripted',speaking_seconds=10,
                window_ids=['turn-1'],cells=[dict(seconds=7 if i==0 else 2 if i==4 else 1 if i==8 else 0,x=.2 if i==0 else (i%3+.5)/3,y=.08 if i==0 else (i//3+.5)/3) for i in range(9)])


class SpatialTests(unittest.TestCase):
    def test_upper_left_not_last_center(self):
        d=decision(attention(),1,'a'*64)
        self.assertEqual(d['cell'],0)
        self.assertEqual(d['percentages'],[70,0,0,0,20,0,0,0,10])
        self.assertEqual(crop_box((1280,720),d),(0,0,640,360))
        self.assertEqual(d['coverage'],1)

    def test_stale_nonfinite_and_false_centroid(self):
        for key,val in [('cycle',2),('source_hash','wrong'),('speaking_seconds',float('nan'))]:
            p=attention();p[key]=val
            with self.assertRaises(ValueError):decision(p,1,'a'*64)
        p=attention();p['cells'][0]['y']=.9
        with self.assertRaises(ValueError):decision(p,1,'a'*64)

    def test_tie_and_coverage(self):
        p=attention();p['cells'][0]['seconds']=2;p['cells'][8]['seconds']=0
        d=decision(p,1,'a'*64)
        self.assertEqual(d['cell'],0);self.assertEqual(d['coverage'],.4)

    def test_freeze_once_and_private_notes_excluded(self):
        s=fixture();s['source_hash']='a'*64
        command(s,'spatial_decision',attention(),'participant')
        self.assertEqual(participant_view(s)['spatialDecision']['cell'],0)
        self.assertNotIn('PRIVATE',str(participant_view(s)))
        with self.assertRaises(ValueError):command(s,'spatial_decision',attention(),'participant')
        s['status']='paused'
        with self.assertRaises(ValueError):command(s,'spatial_decision',attention(),'participant')

    def test_brief_is_bounded_and_only_approved_text(self):
        self.assertIn('pink oval',visual_brief('pink oval'))
        with self.assertRaises(ValueError):visual_brief('x'*601)

class EntryApiTests(unittest.TestCase):
    def setUp(self):
        from test_service import ServiceTests
        ServiceTests.setUp(self)
    def tearDown(self):
        self.client.close();self.temp.cleanup()
    def test_missing_decision_and_invalid_frame_rejected_before_billing(self):
        r=self.client.post('/api/sessions/session-test/region-entry',json={'excerpt':'blue glow'})
        self.assertEqual(r.status_code,422)
        self.assertEqual(self.app.state.store.jobs('session-test'),[])
        self.assertEqual(self.client.get('/api/sessions/session-test/media/bad/frame/final').status_code,404)
    def test_participant_cannot_generate_or_approve(self):
        from test_service import ServiceTests
        guest,headers,_=ServiceTests.participant(self)
        try:
            for path,body in (('region-entry',{'excerpt':'pink oval'}),('media/apply',{'job_id':'bad','continuity_confirmed':True}),('canonical-scene',{})):
                self.assertEqual(guest.post('/api/sessions/session-test/'+path,json=body,headers=headers).status_code,401)
        finally:guest.close()
    def test_scene_hash_freeze_and_pause_block_apply(self):
        import base64,io
        from PIL import Image
        buf=io.BytesIO();Image.new('RGB',(1280,720)).save(buf,format='PNG')
        self.assertEqual(self.client.post('/api/sessions/session-test/scene',json={'image':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}).status_code,200)
        s=self.client.get('/api/sessions/session-test').json()
        import hashlib
        self.assertEqual(s['source_hash'],hashlib.sha256(self.client.get('/api/sessions/session-test/scene').content).hexdigest())
        p=attention();p['source_hash']=s['source_hash']
        response=self.client.post('/api/sessions/session-test/commands',json={'command_id':'spatial-test-1','command':'spatial_decision','payload':p})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['session']['spatialDecision']['cell'],0)
        self.assertEqual(self.client.post('/api/sessions/session-test/transition-complete',json={'job_id':'bad'}).status_code,422)


class VoiceEventTests(unittest.TestCase):
    def test_live_user_transcription_shape_and_legacy(self):
        from inner_landscape.voice_events import transcript
        for key in ('user_transcription_event','user_transcript_event'):
            self.assertEqual(transcript({'type':'user_transcript',key:{'user_transcript':'pink oval'}}),('reflection','pink oval'))
        self.assertIsNone(transcript({'type':'audio'}))

class ManualSelectionTests(unittest.TestCase):
    def test_explicit_selection_is_not_fabricated_dwell(self):
        from inner_landscape.region_zoom import manual_decision
        p=dict(cycle=1,source_hash='a'*64,input_mode='mouse',x=.2,y=.08)
        d=manual_decision(p,1,'a'*64)
        self.assertEqual(d['cell'],0);self.assertTrue(d['manual'])
        self.assertEqual(d['speaking_seconds'],0);self.assertEqual(sum(d['percentages']),0)
        p['x']=float('nan')
        with self.assertRaises(ValueError):manual_decision(p,1,'a'*64)

class ObjectApproachPromptTests(unittest.TestCase):
    def test_target_is_recentered_and_motion_is_object_enlargement(self):
        from inner_landscape.region_zoom import entry_image_prompt, entry_video_prompt
        selected=decision(attention(),1,'a'*64)
        still=entry_image_prompt(visual_brief('blue star'),selected)
        self.assertIn('40% from the left and 16% from the top',still)
        self.assertIn('new nearby objects derived from its silhouette',still)
        video=entry_video_prompt(visual_brief('blue star'))
        self.assertIn('anchor shape grows larger',video)
        self.assertIn('several distinct',video)


class ResolutionBudgetTests(unittest.TestCase):
    def test_video_reserves_enhancement_and_legacy_jobs_still_count(self):
        from inner_landscape.region_zoom import billable_units, enhancement_factor
        self.assertEqual(billable_units([{}, {'billable_units':2}]),3)
        self.assertEqual(enhancement_factor((1280,720)),2)
        with self.assertRaises(ValueError):enhancement_factor((320,180))

class EnhancementTests(unittest.IsolatedAsyncioTestCase):
    async def test_enhancement_preserves_raw_frame_and_validates_real_output_size(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock, patch
        from PIL import Image
        from inner_landscape.providers import Media
        with tempfile.TemporaryDirectory() as folder:
            work=Path(folder);directory=work/'media'/'test';directory.mkdir(parents=True)
            Image.new('RGB',(1280,720),'pink').save(directory/'final.png')
            handle=SimpleNamespace(request_id='enhancement-test',get=AsyncMock(return_value={'image':{'url':'https://fal.media/test.png'}}))
            client=SimpleNamespace(upload_file=AsyncMock(return_value='https://fal.media/input.png'),submit=AsyncMock(return_value=handle))
            async def download(url,path,limit):Image.new('RGB',(2560,1440),'pink').save(path)
            service=Media(SimpleNamespace(work=work),Mock())
            job={'id':'test'}
            with patch('inner_landscape.providers.download',download):await service.enhance_final(client,job,directory)
            self.assertEqual(job['final_resolution'],[2560,1440])
            self.assertEqual(job['upscale_request_id'],'enhancement-test')
            with Image.open(directory/'final-original.png') as image:self.assertEqual(image.size,(1280,720))
            self.assertEqual(client.submit.call_args.args[0],'fal-ai/clarity-upscaler')

    async def test_budget_rejects_video_enhancement_before_submission(self):
        import base64,io,tempfile
        from pathlib import Path
        from unittest.mock import Mock,patch
        from PIL import Image
        from inner_landscape.providers import Media
        from inner_landscape.config import Settings
        with tempfile.TemporaryDirectory() as folder:
            store=Mock();store.jobs.return_value=[{'kind':'image','entry':None,'billable_units':3}]
            service=Media(Settings(root=Path(folder),paid_enabled=True,fal_key='unit-test-only'),store)
            buffer=io.BytesIO();Image.new('RGB',(640,360)).save(buffer,format='PNG')
            with patch('inner_landscape.providers.shutil.which',return_value='/fake/ffprobe'):
                with self.assertRaisesRegex(ValueError,'limit'):
                    await service.submit({'id':'test','cycle':1,'region':'ridge'},'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),'approved brief','video',entry={'cell':0})
            self.assertFalse(service.tasks)
