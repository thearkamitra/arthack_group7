"""Ephemeral browser-to-Unity controls. Frames/poses are never written to sessions."""
import time


class DemoBridge:
    def __init__(self):
        self.states = {}
        self.offer = None

    def state(self, sid):
        return self.states.setdefault(sid, dict(enabled=False, yaw=0, pitch=0, freeze=0,
            simulating=False, simulation=None, presence_at=0, input_mode='', busy=False, speaking=False, speech_at=0,
            window_id='', speech_seq=-1, frame=None, frame_at=0))

    def snapshot(self, sid):
        s = self.state(sid)
        connected = time.monotonic()-s['presence_at'] < 3
        return dict(enabled=s['enabled'], connected=connected,
            headset=connected and s['input_mode']=='xr', busy=s['simulating'] or (s['busy'] if connected else False), simulation=s['simulation'],
            yaw=s['yaw'], pitch=s['pitch'], freeze=s['freeze'],
            speaking=s['speaking'] and time.monotonic()-s['speech_at'] < 1,
            window_id=s['window_id'], voice_frontend=time.monotonic()-s['speech_at']<1, frame_ready=connected and s['input_mode']!='xr' and s['frame'] is not None and time.monotonic()-s['frame_at']<3)

    def input(self, sid, action):
        s=self.state(sid);v=self.snapshot(sid)
        if not s['enabled'] or not v['connected'] or v['headset'] or v['busy']:
            raise ValueError('Browser camera control unavailable: connect Editor demo without headset')
        if action=='left':s['yaw']=max(-110,s['yaw']-5)
        elif action=='right':s['yaw']=min(110,s['yaw']+5)
        elif action=='up':s['pitch']=max(-70,s['pitch']-5)
        elif action=='down':s['pitch']=min(70,s['pitch']+5)
        elif action=='center':s['yaw']=s['pitch']=0
        elif action=='freeze':s['freeze']+=1
        else:raise ValueError('Unknown camera action')
        return self.snapshot(sid)
