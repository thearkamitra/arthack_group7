import base64
import hashlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from inner_landscape.demo_media import make_demo_bundle
from inner_landscape.region_zoom import billable_units
import test_service as service


def frame():
    image=Image.new('RGB',(320,180),'coral')
    image.paste('blue',(0,0,160,90))
    buffer=io.BytesIO();image.save(buffer,format='JPEG');return buffer.getvalue()

class BundleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'local video tools required')
    def test_real_local_clip_has_expected_duration_dimensions_and_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'run'
            result=make_demo_bundle(frame(),directory,321,181)
            self.assertEqual(result['final_resolution'],[320,180])
            self.assertAlmostEqual(result['validation']['duration_seconds'],5,places=1)
            self.assertNotEqual(result['frame_hashes']['first.png'],result['frame_hashes']['final.png'])
            self.assertEqual(result['input_sha256'],hashlib.sha256(frame()).hexdigest())
    def test_invalid_size_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'run'
            with self.assertRaises(ValueError):make_demo_bundle(frame(),target,90000,180)
            self.assertFalse(target.exists())

class SimulationApiTests(unittest.TestCase):
    def setUp(self):service.ServiceTests.setUp(self)
    def tearDown(self):service.ServiceTests.tearDown(self)
    def test_simulation_applies_no_billable_job_and_rejects_repeat_until_complete(self):
        state=self.app.state.demo.state('session-test')
        import time
        state.update(enabled=True,presence_at=time.monotonic(),frame_at=time.monotonic(),frame=frame(),input_mode='editor')
        def bundle(raw,directory,width,height):
            directory.mkdir(parents=True)
            for name in ['first.png','final.png']:Image.new('RGB',(width,height),'blue').save(directory/name)
            (directory/'output.mp4').write_bytes(b'fixture')
            return dict(output_path='output.mp4',validation={'duration_seconds':5},final_resolution=[width,height],frame_hashes={'first.png':'first','final.png':'final'})
        with patch('inner_landscape.demo_media.make_demo_bundle',side_effect=bundle) as mocked:
            response=self.client.post('/api/sessions/session-test/demo/simulate',json={'width':320,'height':180})
            self.assertEqual(response.status_code,200,response.text)
            self.assertTrue(response.json()['simulated'])
            saved=self.client.get('/api/sessions/session-test').json()
            self.assertTrue(saved['media']['simulated']);self.assertTrue(saved['spatialDecision']['manual'])
            self.assertEqual(billable_units(self.app.state.store.jobs('session-test')),0)
            self.assertEqual(self.client.post('/api/sessions/session-test/demo/simulate',json={'width':320,'height':180}).status_code,422)
            self.assertEqual(mocked.call_count,1)
    def test_disconnected_simulation_never_starts_generation(self):
        with patch('inner_landscape.demo_media.make_demo_bundle') as mocked:
            self.assertEqual(self.client.post('/api/sessions/session-test/demo/simulate',json={'width':320,'height':180}).status_code,422)
            mocked.assert_not_called()

    def test_pause_during_generation_retains_artifacts_without_applying(self):
        import time
        state=self.app.state.demo.state('session-test')
        state.update(enabled=True,presence_at=time.monotonic(),frame_at=time.monotonic(),frame=frame(),input_mode='editor')
        def paused_bundle(raw,directory,width,height):
            directory.mkdir(parents=True)
            for name in ['first.png','final.png']:Image.new('RGB',(width,height),'blue').save(directory/name)
            (directory/'output.mp4').write_bytes(b'fixture')
            self.app.state.store.mutate('session-test',lambda s:s.update(status='paused'))
            return dict(output_path='output.mp4',validation={'duration_seconds':5},final_resolution=[width,height],frame_hashes={'first.png':'first','final.png':'final'})
        with patch('inner_landscape.demo_media.make_demo_bundle',side_effect=paused_bundle):
            response=self.client.post('/api/sessions/session-test/demo/simulate',json={'width':320,'height':180})
            self.assertEqual(response.status_code,422)
            saved=self.client.get('/api/sessions/session-test').json()
            self.assertNotIn('job_id',saved.get('media',{}))
            self.assertFalse(state['simulating'])
            self.assertEqual(self.app.state.store.jobs('session-test')[0]['status'],'ready')
