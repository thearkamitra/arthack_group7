import io
import base64
import time
import unittest
from unittest.mock import patch
from PIL import Image
from inner_landscape.demo_bridge import DemoBridge
import test_service as service

class BridgeTests(unittest.TestCase):
    def test_connected_editor_moves_but_headset_and_busy_block_controls(self):
        bridge=DemoBridge();s=bridge.state('s');s.update(enabled=True,presence_at=time.monotonic(),input_mode='editor')
        self.assertEqual(bridge.input('s','left')['yaw'],-5)
        self.assertEqual(bridge.input('s','up')['pitch'],-5)
        s['busy']=True
        with self.assertRaises(ValueError):bridge.input('s','right')
        s.update(busy=False,input_mode='xr')
        with self.assertRaises(ValueError):bridge.input('s','right')
        s['presence_at']-=5
        self.assertFalse(bridge.snapshot('s')['connected'])
        with self.assertRaises(ValueError):bridge.input('s','right')
    def test_speech_and_preview_expire(self):
        bridge=DemoBridge();bridge.state('s').update(speaking=True,speech_at=time.monotonic()-2,frame=b'test',frame_at=time.monotonic()-5,presence_at=time.monotonic())
        self.assertFalse(bridge.snapshot('s')['speaking']);self.assertFalse(bridge.snapshot('s')['frame_ready'])

class DemoApiTests(unittest.TestCase):
    def setUp(self):service.ServiceTests.setUp(self)
    def tearDown(self):service.ServiceTests.tearDown(self)
    def test_offer_is_explicit_local_and_single_use(self):
        self.assertEqual(self.client.post('/api/demo/editor-offer',json={}).status_code,404)
        self.assertEqual(self.client.post('/api/sessions/session-test/demo/start').status_code,200)
        self.assertEqual(self.client.post('/api/demo/editor-offer',json={},headers={'Origin':'http://testserver'}).status_code,403)
        offer=self.client.post('/api/demo/editor-offer',json={});self.assertEqual(offer.status_code,200)
        self.assertEqual(self.client.post('/api/demo/editor-offer',json={}).status_code,404)
        self.assertEqual(self.client.post('/api/pair',json=offer.json()).status_code,200)
    def test_participant_presence_and_frame_are_private_and_ephemeral(self):
        guest,headers,_=service.ServiceTests.participant(self)
        try:
            self.client.post('/api/sessions/session-test/demo/start')
            image=io.BytesIO();Image.new('RGB',(960,540),'blue').save(image,format='JPEG')
            r=guest.post('/api/sessions/session-test/demo/presence',json={'input_mode':'editor','busy':False,'frame':base64.b64encode(image.getvalue()).decode()},headers=headers)
            self.assertEqual(r.status_code,200)
            self.assertEqual(self.client.get('/api/sessions/session-test/demo/frame').content,image.getvalue())
            self.assertEqual(guest.get('/api/sessions/session-test/demo/frame',headers=headers).status_code,401)
            self.assertEqual(guest.post('/api/sessions/session-test/demo/input',json={'action':'left'},headers=headers).status_code,401)
            self.assertNotIn('frame',self.app.state.store.read()['workspace']['sessions'][0])
        finally:guest.close()
    def test_headset_priority_still_uses_frontend_speech_timing(self):
        guest,headers,_=service.ServiceTests.participant(self)
        try:
            guest.post('/api/sessions/session-test/demo/presence',json={'input_mode':'xr','busy':False},headers=headers).raise_for_status()
            self.client.post('/api/sessions/session-test/demo/speech',json={'speaking':True,'window_id':'frontend','sequence':1}).raise_for_status()
            snapshot=self.client.get('/api/sessions/session-test').json()['demo']
            self.assertTrue(snapshot['headset']);self.assertTrue(snapshot['voice_frontend']);self.assertTrue(snapshot['speaking'])
            self.assertEqual(self.client.post('/api/sessions/session-test/demo/input',json={'action':'left'}).status_code,422)
            self.assertEqual(guest.post('/api/sessions/session-test/demo/presence',json={'input_mode':'editor','busy':False},headers=headers).status_code,409)
        finally:guest.close()
    def test_out_of_order_speech_cannot_restart_stopped_window(self):
        url='/api/sessions/session-test/demo/speech'
        self.client.post(url,json={'speaking':False,'window_id':'w','sequence':2})
        self.client.post(url,json={'speaking':True,'window_id':'w','sequence':1})
        self.assertFalse(self.client.get('/api/sessions/session-test').json()['demo']['speaking'])
