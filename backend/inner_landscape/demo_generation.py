"""Bounded, explicitly opted-in fal generation for fictional browser demos."""
from __future__ import annotations
import asyncio
import base64
import hashlib
import io
import time
from PIL import Image, ImageOps
from .region_zoom import manual_decision, billable_units
from .providers import ProviderUnavailable

BRIEF = (
    'Discover three to five NEW distinct companion objects around the existing central form: '
    'small floating rounded shapes, curved ribbons, luminous facets and layered sculptural forms. '
    'Derive their silhouettes, colors and materials from this exact view. Preserve the existing '
    'anchor, dark negative space, grainy painted texture and lighting. During the inward camera '
    'approach reveal additional objects progressively through gentle parallax and soft emergence. '
    'Finish with several distinct readable objects to explore, not an enlarged featureless surface. '
    'No text, people, threatening imagery, portals or unrelated scenery.'
)


def assert_current(store, original):
    current=next(s for s in store.read()['workspace']['sessions'] if s['id']==original['id'])
    if current['status']!='active' or current['cycle']!=original['cycle'] or current.get('source_hash')!=original.get('source_hash'):
        raise ValueError('Session paused or changed; generated artifacts retained without continuing')


async def ready_job(store, sid, jid):
    deadline=time.monotonic()+660
    while time.monotonic()<deadline:
        job=next(j for j in store.jobs(sid) if j['id']==jid)
        if job['status']=='ready':return job
        if job['status'] in ('failed','unknown','cancelled'):
            raise ProviderUnavailable(job.get('error') or 'Generation stopped; inspect the existing job before retrying')
        await asyncio.sleep(.5)
    raise ProviderUnavailable('Generation is still pending; inspect the existing job, do not resubmit')


async def generate_view(cfg, media, store, original, frame, width, height, stage):
    if not cfg.paid_enabled or not cfg.fal_key:
        raise ProviderUnavailable('Enable paid generation and configure fal on the Mac first')
    if billable_units(store.jobs(original['id']))+3>cfg.max_jobs:
        raise ValueError('This view needs three fal calls. The session budget is exhausted; start a new demo session.')
    import shutil
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('ffmpeg and ffprobe are required before submitting fal jobs')
    assert_current(store,original)
    with Image.open(io.BytesIO(frame)) as source:
        image=ImageOps.fit(source.convert('RGB'),(width,height),method=Image.Resampling.LANCZOS)
    # Reject an almost empty off-artwork view before any paid call.
    from collections import Counter
    thumbnail=image.resize((64,64))
    colors=Counter(tuple(channel//16 for channel in pixel) for pixel in thumbnail.getdata())
    if max(colors.values())/4096 > .94:
        raise ValueError('This view is mostly empty background. Center the artwork or choose a visible shape before confirming.')
    if not .4<=width/height<=2.5:
        raise ValueError('Use a landscape or portrait view with a supported aspect ratio')
    if min(image.size)<300:
        factor=300/min(image.size)
        image=image.resize((round(width*factor),round(height*factor)),Image.Resampling.LANCZOS)
    buffer=io.BytesIO();image.save(buffer,format='PNG');raw=buffer.getvalue()
    selected=manual_decision(dict(cycle=original['cycle'],source_hash=original.get('source_hash',''),x=.5,y=.5,input_mode='scripted'),original['cycle'],original.get('source_hash',''))
    # The preview already is the chosen view: do not crop its center a second time.
    selected.update(crop=[0,0,1,1],view_sha256=hashlib.sha256(frame).hexdigest(),viewport=[width,height])
    def freeze(current):
        if current['status']!='active' or current['cycle']!=original['cycle'] or current.get('source_hash')!=original.get('source_hash'):
            raise ValueError('View is stale')
        current['spatialDecision']=selected
    store.mutate(original['id'],freeze)
    stage('fal.ai is discovering new related forms')
    image_job=await media.submit(original,'data:image/png;base64,'+base64.b64encode(raw).decode(),BRIEF,'image',entry=selected)
    image_job=await ready_job(store,original['id'],image_job['id'])
    assert_current(store,original)
    start=(cfg.work/'media'/image_job['id']/image_job['output_path']).read_bytes()
    stage('fal.ai is generating the inward journey and final image')
    video=await media.submit(original,'data:image/png;base64,'+base64.b64encode(start).decode(),BRIEF,'video',entry=selected)
    video.update(parent_job=image_job['id'],demo_autoplay=True)
    media.persist(video)
    video=await ready_job(store,original['id'],video['id'])
    assert_current(store,original)
    return video
