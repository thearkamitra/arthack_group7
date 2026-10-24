from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import fal_client
import httpx
from elevenlabs.client import ElevenLabs
from PIL import Image

from .config import Settings
from .domain import now


class ProviderUnavailable(Exception):
    pass


class Voice:
    def __init__(self, settings: Settings):
        self.settings = settings

    def signed_url(self) -> str:
        if not self.settings.paid_enabled:
            raise ProviderUnavailable(
                "Voice is disabled until a paid test is approved and the server is explicitly enabled"
            )
        if not self.settings.eleven_key or not self.settings.agent_id:
            raise ProviderUnavailable(
                "Configure the ElevenLabs key and create the reflection agent first"
            )
        client = ElevenLabs(api_key=self.settings.eleven_key, timeout=20)
        return client.conversational_ai.conversations.get_signed_url(
            agent_id=self.settings.agent_id
        ).signed_url


def decode_image(data: str) -> tuple[Image.Image, bytes]:
    if not data.startswith("data:image/png;base64,") or len(data) > 44_000_000:
        raise ValueError("Use a PNG image under 32 MB")
    try:
        raw = base64.b64decode(data.split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            if (
                im.format != "PNG"
                or im.width * im.height > 8_000_000
                or min(im.size) < 64
            ):
                raise ValueError(
                    "PNG must contain 64px or larger sides and at most 8 million pixels"
                )
            im.load()
            return im.convert("RGB"), raw
    except Exception as exc:
        raise ValueError("Invalid PNG image") from exc


def region_box(size: tuple[int, int], region: str) -> tuple[int, int, int, int]:
    index = {"sky": 0, "ridge": 1, "water": 2}[region]
    w, h = size
    return (int(w * index / 3), 0, int(w * (index + 1) / 3), h)


def trusted_media_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (
        parsed.scheme == "https"
        and not parsed.username
        and (
            host.endswith(".fal.media")
            or host == "fal.media"
            or host == "storage.googleapis.com"
        )
    )


async def download(url: str, target: Path, limit: int) -> None:
    if not trusted_media_url(url):
        raise ValueError("Provider returned an unexpected media host")
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            count = 0
            with target.open("wb") as out:
                async for chunk in response.aiter_bytes():
                    count += len(chunk)
                    if count > limit:
                        raise ValueError("Provider artifact exceeds size limit")
                    out.write(chunk)


def probe_video(path: Path) -> dict:
    binary = shutil.which("ffprobe")
    if not binary:
        raise ProviderUnavailable(
            "ffprobe is required to validate a video before it can be used"
        )
    result = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    value = json.loads(result.stdout)
    duration = float(value["format"]["duration"])
    if not 0 < duration <= 30.001 or not any(
        s.get("codec_type") == "video" and s.get("width", 0) > 0
        for s in value["streams"]
    ):
        raise ValueError("Clip must decode as video and be at most 30 seconds")
    return {"duration_seconds": duration, "streams": value["streams"]}


class Media:
    def __init__(self, settings: Settings, store):
        self.settings = settings
        self.store = store
        self.lock = asyncio.Lock()
        self.tasks: set[asyncio.Task] = set()

    async def submit(
        self, session: dict, image_data: str, brief: str, kind: str, entry: dict | None = None
    ) -> dict:
        if not self.settings.paid_enabled:
            raise ProviderUnavailable(
                "Paid generation is disabled; explicitly enable it after agreeing a budget"
            )
        if not self.settings.fal_key:
            raise ProviderUnavailable("fal.ai key is not configured")
        if kind not in ("image", "video"):
            raise ValueError("Unknown media kind")
        if kind == "video" and not shutil.which("ffprobe"):
            raise ProviderUnavailable(
                "Install ffprobe before video generation; no paid job was submitted"
            )
        if entry and kind == "video" and not shutil.which("ffmpeg"):
            raise ProviderUnavailable("Install ffmpeg before video/final-frame generation")
        image, raw = decode_image(image_data)
        if kind == "video" and (
            min(image.size) < 300 or not 0.4 <= image.width / image.height <= 2.5
        ):
            raise ValueError(
                "Video needs at least 300px per side and an aspect ratio between 0.4 and 2.5"
            )
        if kind == "image" and image.width < 192:
            raise ValueError("Image must be at least 192px wide for region editing")
        if not brief.strip() or len(brief) > 1000:
            raise ValueError("Provide a short visual brief of at most 1000 characters")
        async with self.lock:
            previous = self.store.jobs(session["id"])
            if entry and any(j.get("entry") == entry and j["kind"] == kind for j in previous):
                raise ValueError("Region entry already submitted; reconcile existing job")
            from .region_zoom import billable_units
            units = 2 if entry and kind == "video" else 1
            if billable_units(previous) + units > self.settings.max_jobs:
                raise ValueError("Per-session generation limit reached")
            if any(j["status"] in ("queued", "running", "validating", "unknown") for j in previous):
                raise ValueError(
                    "A job is already pending; reconcile it before submitting another"
                )
            job = {
                "id": str(uuid.uuid4()),
                "session_id": session["id"],
                "cycle": session["cycle"],
                "region": session["region"],
                "entry": entry,
                "billable_units": units,
                "status": "queued",
                "kind": kind,
                "created_at": now(),
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "parameters": {"duration": "5" if kind == "video" else None},
                "model": self.settings.video_model
                if kind == "video"
                else self.settings.image_model,
                "prompt_version": 3 if entry else 1,
                "brief": brief.strip(),
                "request_id": None,
                "output_path": None,
                "region_map_verified": False,
            }
            directory = self.settings.work / "media" / job["id"]
            directory.mkdir(parents=True)
            (directory / "input.png").write_bytes(raw)
            self.persist(job)
            task = asyncio.create_task(self.run(job, image, directory))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return job

    def persist(self, job: dict) -> None:
        self.store.put_job(job)
        directory = self.settings.work / "media" / job["id"]
        directory.mkdir(parents=True, exist_ok=True)
        temp = directory / "manifest.tmp"
        temp.write_text(json.dumps(job, indent=2))
        temp.replace(directory / "manifest.json")

    async def enhance_final(self, client, job: dict, directory: Path) -> None:
        from .region_zoom import enhancement_factor
        raw = directory / "final-original.png"
        shutil.copy2(directory / "final.png", raw)
        with Image.open(raw) as image:
            source_size = image.size
        inputs = {"image_url": await client.upload_file(str(raw)),
                  "upscale_factor": enhancement_factor(source_size),
                  "creativity": 0.1, "resemblance": 1.0,
                  "prompt": "Detailed abstract artwork. Preserve the exact shapes, placement, palette and soft painted grain of this frame. Crisp edges and fine material detail.",
                  "negative_prompt": "new objects, changed composition, text, glyphs, blur, oversharpening",
                  "enable_safety_checker": True}
        job["upscale_input_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
        job["stage"] = "enhancing_final"
        job["upscale_model"] = "fal-ai/clarity-upscaler"
        job["upscale_parameters"] = {k: v for k, v in inputs.items() if k != "image_url"}
        self.persist(job)
        handle = await client.submit(job["upscale_model"], arguments=inputs)
        job["upscale_request_id"] = handle.request_id
        self.persist(job)
        result = await asyncio.wait_for(handle.get(), timeout=300)
        enhanced = directory / "enhanced.png"
        await download(result["image"]["url"], enhanced, 40_000_000)
        with Image.open(enhanced) as image:
            image.load()
            if max(image.size) < 2560 or image.width * image.height > 8_000_000 or abs(image.width/image.height-source_size[0]/source_size[1]) > .02:
                raise ValueError("Enhanced frame failed resolution/aspect validation")
            image.convert("RGB").save(directory / "final.png")
            job["final_resolution"] = list(image.size)
        job["stage"] = "validated"

    async def run(self, job: dict, original: Image.Image, directory: Path) -> None:
        submitted = False
        try:
            client = fal_client.AsyncClient(key=self.settings.fal_key)
            prompt = (
                "Abstract space, preserve the input palette and texture, no text, no people, no threatening imagery. "
                + job["brief"]
            )
            if job["kind"] == "image":
                from .region_zoom import crop_box, entry_image_prompt
                box = crop_box(original.size, job["entry"]) if job.get("entry") else region_box(original.size, job["region"])
                crop = directory / "crop.png"
                original.crop(box).save(crop)
                url = await client.upload_file(str(crop))
                inputs = {
                    "prompt": entry_image_prompt(prompt, job["entry"]) if job.get("entry") else prompt,
                    "image_url": url,
                    "output_format": "png",
                    "num_images": 1,
                    "enable_safety_checker": True,
                }
            else:
                video_input = directory / "video-input.jpg"
                original.save(video_input, quality=95)
                if video_input.stat().st_size > 10_000_000:
                    raise ValueError("Video input exceeds the provider size limit")
                job["video_input_sha256"] = hashlib.sha256(video_input.read_bytes()).hexdigest()
                url = await client.upload_file(str(video_input))
                from .region_zoom import entry_video_prompt
                inputs = {
                    "prompt": entry_video_prompt(prompt) if job.get("entry") else prompt + " Locked camera. Very gentle environmental motion. Preserve composition and landmarks.",
                    "image_url": url,
                    "duration": "5",
                    "enable_safety_checker": True,
                }
            if job.get("entry") and job["kind"] == "video":
                inputs["negative_prompt"] = "zoom out, pull back, dolly backward, shrinking subject, widening view, tunnel, corridor, nested frames, unrelated scenery, featureless surface, blurred macro texture, cuts, embossed glyphs"
            job["generation_prompt"] = inputs["prompt"]
            job["status"] = "running"
            self.persist(job)
            submitted = True
            handle = await client.submit(job["model"], arguments=inputs)
            job["request_id"] = handle.request_id
            self.persist(job)
            # Cancellation or timeout must not cause automatic paid resubmission.
            result = await asyncio.wait_for(handle.get(), timeout=300)
            job["status"] = "validating"
            self.persist(job)
            output = directory / (
                "output.png" if job["kind"] == "image" else "output.mp4"
            )
            if job["kind"] == "image":
                if any(result.get("has_nsfw_concepts", [])):
                    raise ValueError("Provider safety checker blocked the image")
                remote = result["images"][0]["url"]
                edited = directory / "edited.png"
                await download(remote, edited, 30_000_000)
                with Image.open(edited) as im:
                    im.load()
                    native = im.convert("RGB").copy()
                    patch = native.resize((box[2] - box[0], box[3] - box[1]))
                composite = native if job.get("entry") else original.copy()
                if not job.get("entry"):
                    composite.paste(patch, box)
                composite.save(output)
                job["validation"] = {
                    "decoded": True,
                    "width": composite.width,
                    "height": composite.height,
                    "unchanged_outside_crop": not bool(job.get("entry")),
                }
            else:
                remote = result["video"]["url"]
                await download(remote, output, 150_000_000)
                job["validation"] = await asyncio.to_thread(probe_video, output)
                if job.get("entry"):
                    import subprocess
                    for name, args, tail in (("first.png", ["-i", str(output)], ["-frames:v", "1"]), ("final.png", ["-sseof", "-0.5", "-i", str(output)], ["-update", "1"])):
                        await asyncio.to_thread(subprocess.run, ["ffmpeg", "-v", "error", "-y", *args, *tail, str(directory/name)], check=True, capture_output=True, timeout=30)
                        with Image.open(directory/name) as frame:
                            frame.verify()
                    await self.enhance_final(client, job, directory)
                    job["frame_hashes"] = {n: hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in ("first.png","final.png")}
            job["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
            job["output_path"] = output.name
            job["status"] = "ready"
            job["completed_at"] = now()
        except asyncio.CancelledError:
            job["status"] = "unknown" if submitted else "cancelled"
            job["error"] = (
                "Server stopped; reconcile the provider request before retrying"
            )
            raise
        except asyncio.TimeoutError:
            job["status"] = "unknown"
            job["error"] = "Provider result timed out; do not resubmit automatically"
        except Exception as exc:
            job["status"] = (
                "unknown" if submitted and (not job.get("request_id") or (job.get("stage") == "enhancing_final" and not job.get("upscale_request_id"))) else "failed"
            )
            job["error"] = (
                "Generation did not produce a validated artifact ("
                + type(exc).__name__
                + "). Keep the previous scene."
            )
        finally:
            self.persist(job)
