"""Deterministic local demo media; never calls a provider or claims AI generation."""
from __future__ import annotations
import hashlib
import io
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageOps
from .providers import probe_video


def make_demo_bundle(frame: bytes, directory: Path, width: int, height: int) -> dict:
    if type(width) is not int or type(height) is not int or not (160 <= width <= 1280 and 90 <= height <= 720):
        raise ValueError('Demo viewport must be between 160×90 and 1280×720')
    # H.264 yuv420p requires even dimensions.
    width -= width % 2; height -= height % 2
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('ffmpeg is required for local demo playback')
    with Image.open(io.BytesIO(frame)) as source:
        source.load()
        image = ImageOps.fit(source.convert('RGB'), (width, height), method=Image.Resampling.LANCZOS)
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'input.jpg').write_bytes(frame)
    image.save(directory/'first.png')
    zoom = f"zoompan=z='1+0.22*on/149':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={width}x{height}:fps=30"
    command = [ffmpeg,'-v','error','-loop','1','-i',str(directory/'first.png'),'-vf',zoom,'-t','5','-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(directory/'output.mp4')]
    subprocess.run(command, check=True, capture_output=True, timeout=40)
    validation = probe_video(directory/'output.mp4')
    extract = [ffmpeg,'-v','error','-sseof','-0.04','-i',str(directory/'output.mp4'),'-frames:v','1',str(directory/'final.png')]
    subprocess.run(extract, check=True, capture_output=True, timeout=10)
    with Image.open(directory/'final.png') as last:
        if last.size != (width,height):
            raise ValueError('Demo final frame has unexpected dimensions')
    return dict(output_path='output.mp4', validation=validation, final_resolution=[width,height],
                commands=[command,extract], input_sha256=hashlib.sha256(frame).hexdigest(),
                frame_hashes={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ('first.png','final.png')})
