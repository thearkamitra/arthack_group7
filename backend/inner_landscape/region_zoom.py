"""Versioned spatial attention and region-entry contracts; no provider dependencies."""
from __future__ import annotations
import math
import re


def decision(payload: dict, cycle: int, source_hash: str) -> dict:
    if payload.get('cycle') != cycle or payload.get('source_hash') != source_hash:
        raise ValueError('Stale cycle or source image')
    cells = payload.get('cells', [])
    if not isinstance(cells, list) or len(cells) != 9:
        raise ValueError('Expected nine row-major cells')
    def number(v, low, high):
        if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError('Invalid attention value')
        return float(v)
    seconds = [number(c.get('seconds'), 0, 120) for c in cells]
    total = sum(seconds)
    speaking = number(payload.get('speaking_seconds'), 0, 120)
    if total < .5 or total > speaking + .05:
        raise ValueError('Insufficient or inconsistent attention')
    windows = payload.get('window_ids')
    if not isinstance(windows, list) or not 1 <= len(windows) <= 50 or any(not isinstance(w,str) or not 1 <= len(w) <= 100 for w in windows) or len(set(windows)) != len(windows):
        raise ValueError('Invalid speech windows')
    mode = payload.get('input_mode')
    if mode not in ('xr', 'mouse', 'scripted'):
        raise ValueError('Unknown attention source')
    for i, c in enumerate(cells):
        x, y = number(c.get('x'), 0, 1), number(c.get('y'), 0, 1)
        if seconds[i] and (min(2,int(x*3)) != i%3 or min(2,int(y*3)) != i//3):
            raise ValueError('Centroid outside cell')
    winner = max(range(9), key=lambda i: seconds[i])
    x,y = cells[winner]['x'],cells[winner]['y']
    left,top = max(0,min(.5,x-.25)), max(0,min(.5,y-.25))
    return dict(version=1, cycle=cycle, source_hash=source_hash, cell=winner,
                x=x,y=y,crop=[left,top,left+.5,top+.5],cells=cells,
                percentages=[s/total*100 for s in seconds], coverage=min(1.0,total/speaking),
                speaking_seconds=speaking, window_ids=windows,input_mode=mode)


def crop_box(size: tuple[int,int], selected: dict) -> tuple[int,int,int,int]:
    w,h=size
    l,t,r,b=selected['crop']
    return round(l*w),round(t*h),round(r*w),round(b*h)


def visual_brief(text: str) -> str:
    # Caller supplies explicitly approved conversational excerpt, never session notes.
    if not isinstance(text,str) or not 1 <= len(text.strip()) <= 600:
        raise ValueError('Approve a short conversation excerpt (1–600 characters)')
    text=re.sub(r'\s+',' ',text).strip()
    return ('Make a much closer view of the selected existing object. Preserve its identity, '
            'soft grain, luminous shapes and source palette. Visual direction from the '
            'approved fictional or consented conversation: '+text)


def manual_decision(payload: dict, cycle: int, source_hash: str) -> dict:
    """Explicit confirmation when there was no valid audible guide window."""
    if payload.get('cycle') != cycle or payload.get('source_hash') != source_hash:
        raise ValueError('Stale cycle or source image')
    x, y = payload.get('x'), payload.get('y')
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in (x, y)):
        raise ValueError('Invalid confirmed image point')
    if payload.get('input_mode') not in ('xr','mouse','scripted'):
        raise ValueError('Unknown attention source')
    left, top = max(0,min(.5,x-.25)), max(0,min(.5,y-.25))
    return dict(version=1,cycle=cycle,source_hash=source_hash,manual=True,
                input_mode=payload['input_mode'],x=x,y=y,cell=min(2,int(x*3))+3*min(2,int(y*3)),
                crop=[left,top,left+.5,top+.5],cells=[],percentages=[0]*9,
                coverage=0,speaking_seconds=0,window_ids=[])



def entry_image_prompt(brief: str, selected: dict) -> str:
    left, top, right, bottom = selected['crop']
    x = (selected['x'] - left) / (right - left)
    y = (selected['y'] - top) / (bottom - top)
    return (f'The selected object is at {x:.0%} from the left and {y:.0%} from the top '
            'of this input crop. Reframe tightly around that existing object and place it '
            'at the center. Magnify it into a close-up so its luminous surface occupies '
            'most of the frame and surrounding shapes leave the edges. Preserve its '
            'original silhouette, soft painted grain and colors. '+brief+
            ' Do not add a room, corridor, tunnel, frames, glyphs or new surrounding scenery. '
            'Do not widen the composition or move away from the object.')


def entry_video_prompt(brief: str) -> str:
    return ('One continuous forward camera push directly INTO the selected object at '
            'the CENTER of the first frame. Begin with the supplied close-up. Move '
            'steadily closer: the same object grows larger every second, its outer '
            'edges pass beyond the image boundaries, and finish with its luminous '
            'surface texture filling the entire frame. This is a macro approach to '
            'the object, with no newly revealed surrounding space. Preserve its colors '
            'and soft grain. No cuts, orbit, receding object, tunnel or pullback. '+brief)
