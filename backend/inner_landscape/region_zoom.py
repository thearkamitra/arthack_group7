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
    return ('Reveal new nearby forms while moving closer to the selected existing shape. Preserve its identity, '
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
    return (f'The selected shape is at {x:.0%} from the left and {y:.0%} from the top '
            'of this input crop. Bring that existing shape closer and keep it recognizable. '
            'Reveal a few new nearby objects derived from its silhouette: smaller companion '
            'shapes, curved ribbons, luminous facets and layered forms. They share its '
            'palette, soft grain and shape language, rather than unrelated scenery. '
            'Keep a detailed composition with distinct forms and room to explore between '
            'them. '+brief+' No text, embossed glyphs, room or nested tunnel frames.')


def entry_video_prompt(brief: str) -> str:
    return ('One continuous slow forward push TOWARD the selected shape in the input. '
            'The anchor shape grows larger while new nearby companion objects and layered '
            'forms gradually emerge beside and within its luminous contours. These new '
            'forms echo the same silhouette, colors and soft painted material. Reveal '
            'local detail by moving closer, never by pulling back or widening the view. '
            'End on a crisp, richly detailed closer composition with several distinct '
            'related shapes visible and a recognizable part of the original anchor. '
            'Hold the final composition steady. No featureless surface filling the frame, '
            'blurred macro texture, cuts, orbit or nested tunnel frames. '+brief)


def billable_units(jobs: list[dict]) -> int:
    return sum(j.get('billable_units', 1) for j in jobs)


def enhancement_factor(size: tuple[int, int]) -> float:
    factor = max(1.0, 2560 / max(size))
    if factor > 4:
        raise ValueError('Final frame is too small for bounded high-resolution enhancement')
    return factor
