import asyncio
import base64
import io
import time
import unittest
from dataclasses import replace
from PIL import Image
from inner_landscape.demo_generation import generate_view, BRIEF
import test_service as service

class GenerationTests(unittest.TestCase):
    def setUp(self):
        service.ServiceTests.setUp(self)
        self.cfg=replace(self.app.state.settings,paid_enabled=True,fal_key='offline-test-key')
        self.original=self.client.get('/api/sessions/session-test').json()
        buffer=io.BytesIO();image=Image.new('RGB',(960,540),'coral');image.paste('blue',(0,0,480,270));image.save(buffer,format='JPEG');self.frame=buffer.getvalue()
        self.calls=[];self.pause_after_image=False
        owner=self
        class FakeMedia:
            async def submit(inner,session,image_data,brief,kind,entry=None):
                owner.calls.append((kind,image_data,brief,entry))
                jid='offline-'+kind
                folder=owner.cfg.work/'media'/jid;folder.mkdir(parents=True)
                if kind=='image':
                    raw=base64.b64decode(image_data.split(',',1)[1]);(folder/'output.png').write_bytes(raw)
                job=dict(id=jid,session_id=session['id'],kind=kind,status='ready',entry=entry,output_path='output.png' if kind=='image' else 'output.mp4',billable_units=1 if kind=='image' else 2)
                owner.app.state.store.put_job(job)
                if owner.pause_after_image and kind=='image':owner.app.state.store.mutate(session['id'],lambda s:s.update(status='paused'))
                return job
            def persist(inner,job):owner.app.state.store.put_job(job)
        self.media=FakeMedia()
    def tearDown(self):service.ServiceTests.tearDown(self)
    def run_generation(self):
        return asyncio.run(generate_view(self.cfg,self.media,self.app.state.store,self.original,self.frame,668,376,lambda msg:None))
    def test_uses_whole_confirmed_view_and_new_objects_with_two_sequential_jobs(self):
        result=self.run_generation()
        self.assertEqual([c[0] for c in self.calls],['image','video'])
        self.assertEqual(self.calls[0][3]['crop'],[0,0,1,1])
        self.assertEqual(self.calls[0][3]['viewport'],[668,376])
        self.assertIn('NEW distinct companion objects',BRIEF)
        self.assertNotIn('PRIVATE',self.calls[0][2])
        self.assertTrue(result['demo_autoplay']);self.assertEqual(result['parent_job'],'offline-image')
    def test_pause_after_still_prevents_a_billable_video_submission(self):
        self.pause_after_image=True
        with self.assertRaisesRegex(ValueError,'paused or changed'):self.run_generation()
        self.assertEqual(len(self.calls),1)
    def test_budget_is_checked_before_any_provider_call(self):
        self.app.state.store.put_job(dict(id='old',session_id=self.original['id'],billable_units=3))
        with self.assertRaisesRegex(ValueError,'budget is exhausted'):self.run_generation()
        self.assertEqual(self.calls,[])
    def test_route_requires_explicit_autoplay_before_generation(self):
        from unittest.mock import patch
        with patch('inner_landscape.demo_generation.generate_view') as generate:
            result=self.client.post('/api/sessions/session-test/demo/generate',json={'width':668,'height':376})
            self.assertEqual(result.status_code,422);generate.assert_not_called()

    def test_empty_background_is_rejected_before_billing(self):
        buffer=io.BytesIO();Image.new('RGB',(960,540),'white').save(buffer,format='JPEG');self.frame=buffer.getvalue()
        with self.assertRaisesRegex(ValueError,'mostly empty background'):self.run_generation()
        self.assertEqual(self.calls,[])
