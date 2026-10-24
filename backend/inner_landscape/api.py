from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import websockets
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .garmin import HeartRateMonitor
from .garmin_ble import GarminBLE
from .config import Settings
from .domain import command, event, participant_view
from .providers import Media, ProviderUnavailable, Voice, decode_image
from .store import Conflict, Store


class WorkspaceBody(BaseModel):
    revision: int = Field(ge=0)
    workspace: dict


class CommandBody(BaseModel):
    command_id: str = Field(min_length=8, max_length=100)
    command: str
    payload: dict = Field(default_factory=dict)


class HeartRateBody(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    consent: bool = False


class PairBody(BaseModel):
    code: str = Field(min_length=8, max_length=8)


class MediaBody(BaseModel):
    image: str = Field(max_length=44_000_000)
    brief: str = Field(min_length=1, max_length=1000)
    kind: str = "image"


class EntryBody(BaseModel):
    excerpt: str = Field(min_length=1, max_length=600)
    parent_job: str | None = None


class ApplyBody(BaseModel):
    job_id: str
    continuity_confirmed: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.load()
    store = Store(cfg.work / "sessions.sqlite3")
    media = Media(cfg, store)
    voice = Voice(cfg)
    admin_token = secrets.token_urlsafe(40)
    heart_rate = HeartRateMonitor()
    garmin = GarminBLE(heart_rate)

    def reconcile_heart_rate():
        heart_rate.reconcile({s["id"] for s in store.read()["workspace"]["sessions"] if s["status"] == "active"})

    @asynccontextmanager
    async def lifespan(app):
        async def cleanup():
            while True:
                reconcile_heart_rate()
                garmin.devices = {key: value for key, value in garmin.devices.items() if time.monotonic() - value[1] <= 60}
                await asyncio.sleep(1)
        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await garmin.stop()

    app = FastAPI(
        lifespan=lifespan,
        title="Inner Landscape coordinator",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.garmin = garmin
    app.state.heart_rate = heart_rate
    app.state.store = store
    app.state.settings = cfg
    app.state.media = media
    active_voice: set[str] = set()
    pair_attempts: dict[str, list[float]] = {}

    def therapist(request: Request) -> None:
        if not secrets.compare_digest(
            request.cookies.get("landscape_admin", ""), admin_token
        ):
            raise HTTPException(
                401, "Open the workspace on the Mac to authenticate this local demo"
            )

    def session(sid: str) -> dict:
        item = next(
            (s for s in store.read()["workspace"]["sessions"] if s["id"] == sid), None
        )
        if not item:
            raise HTTPException(404, "Session not found")
        return item

    def role(request: Request, sid: str) -> str:
        if secrets.compare_digest(
            request.cookies.get("landscape_admin", ""), admin_token
        ):
            return "therapist"
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if store.token_session(token) == sid:
            return "participant"
        raise HTTPException(401, "Pair this participant to the session")

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if int(request.headers.get("content-length", "0") or "0") > 45_000_000:
            return JSONResponse({"detail": "Request too large"}, 413)
        origin = request.headers.get("origin")
        if (
            request.url.path.startswith("/api/")
            and origin
            and urlparse(origin).netloc != request.headers.get("host")
        ):
            return JSONResponse({"detail": "Cross-origin API calls are disabled"}, 403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        # The root of the loopback demo is the explicit local practitioner bootstrap.
        # Never issue practitioner cookies to LAN participants or via DNS aliases.
        if (
            request.url.path in ("/", "/index.html")
            and request.client
            and request.client.host in ("127.0.0.1", "::1", "testclient")
            and request.url.hostname in ("127.0.0.1", "localhost", "testserver")
        ):
            response.set_cookie(
                "landscape_admin",
                admin_token,
                httponly=True,
                samesite="strict",
                secure=False,
                max_age=86400,
            )
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, 422)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, 409)

    @app.exception_handler(ProviderUnavailable)
    async def unavailable(request, exc):
        return JSONResponse({"detail": str(exc)}, 503)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Record not found"}, 404)

    @app.get("/api/status")
    def status(request: Request):
        therapist(request)
        return {
            "service": "inner-landscape",
            "schema_version": 1,
            "paid_enabled": cfg.paid_enabled,
            "voice": {
                "configured": bool(cfg.eleven_key and cfg.agent_id),
                "connected": False,
            },
            "media": {"configured": bool(cfg.fal_key), "connected": False},
            "garmin": {"status": "mac_ble", "connected": garmin.state == "connected", "ephemeral": True},
            "hardware_verified": False,
        }

    @app.get("/api/workspace")
    def read_workspace(request: Request):
        therapist(request)
        return store.read()

    @app.put("/api/workspace")
    async def write_workspace(body: WorkspaceBody, request: Request):
        therapist(request)
        result = store.replace(body.workspace, body.revision)
        reconcile_heart_rate()
        if heart_rate.sid is None and garmin.task and not garmin.task.done():
            await garmin.stop()
        return result

    @app.post("/api/garmin/scan")
    async def scan_garmin(request: Request):
        therapist(request)
        return await garmin.scan()

    @app.post("/api/sessions/{sid}/heart-rate/start")
    async def start_heart_rate(sid: str, body: HeartRateBody, request: Request):
        therapist(request)
        if session(sid)["status"] != "active":
            raise HTTPException(409, "Resume before connecting heart rate")
        reconcile_heart_rate()
        if not body.consent:
            raise ValueError("Confirm local heart-rate monitoring before connecting")
        return await garmin.start(sid, body.device_id)

    @app.get("/api/sessions/{sid}/heart-rate")
    def read_heart_rate(sid: str, request: Request):
        therapist(request)
        session(sid)
        reconcile_heart_rate()
        return garmin.view(sid, request.headers.get("x-garmin-token", ""))

    @app.post("/api/sessions/{sid}/heart-rate/stop")
    async def stop_heart_rate(sid: str, request: Request):
        therapist(request)
        if heart_rate.sid is not None:
            heart_rate.authorize(sid, request.headers.get("x-garmin-token", ""))
        await garmin.stop()
        return garmin.view(sid)

    @app.post("/api/sessions/{sid}/pair")
    def make_pair(sid: str, request: Request):
        therapist(request)
        if session(sid)["status"] == "completed":
            raise HTTPException(409, "Session completed")
        return {"code": store.pair(sid), "expires_in_seconds": 120}

    @app.post("/api/pair")
    def redeem_pair(body: PairBody, request: Request):
        address = request.client.host if request.client else "unknown"
        recent = [
            t for t in pair_attempts.get(address, []) if time.monotonic() - t < 60
        ]
        if len(recent) >= 10:
            raise HTTPException(429, "Wait a minute before retrying pairing")
        pair_attempts[address] = recent + [time.monotonic()]
        result = store.redeem(body.code)
        if not result:
            raise HTTPException(401, "Pairing code expired or incorrect")
        token, sid = result
        if session(sid)["status"] == "completed":
            raise HTTPException(409, "Session completed")
        store.mutate(sid, lambda s: s.update(driver="unity"))
        return {"token": token, "session_id": sid, "expires_in_seconds": 3600}

    @app.get("/api/sessions/{sid}")
    def read_session(sid: str, request: Request):
        access = role(request, sid)
        value = session(sid)
        return value if access == "therapist" else participant_view(value)

    @app.post("/api/sessions/{sid}/commands")
    async def send_command(sid: str, body: CommandBody, request: Request):
        access = role(request, sid)
        if access == "participant" and body.command == "resume":
            # A therapist must explicitly resume after pause/tracking loss.
            raise HTTPException(403, "Ask the practitioner to resume")
        if body.command == "attention" and body.payload.get("source") != "head":
            raise ValueError("Headset attention must identify its source")
        result = store.mutate(
            sid,
            lambda s: command(s, body.command, body.payload, access),
            body.command_id,
        )
        reconcile_heart_rate()
        if heart_rate.sid is None and garmin.task and not garmin.task.done():
            await garmin.stop()
        return {
            "revision": result["revision"],
            "session": result["session"]
            if access == "therapist"
            else participant_view(result["session"]),
        }

    @app.websocket("/api/sessions/{sid}/events")
    async def events(ws: WebSocket, sid: str):
        await ws.accept()
        try:
            auth = await asyncio.wait_for(ws.receive_json(), timeout=10)
            access = secrets.compare_digest(
                ws.cookies.get("landscape_admin", ""), admin_token
            )
            if not access and store.token_session(auth.get("token", "")) != sid:
                await ws.close(4401)
                return
            origin = ws.headers.get("origin")
            if origin and urlparse(origin).netloc != ws.headers.get("host"):
                await ws.close(4403)
                return
            last = -1
            while True:
                snap = store.read()
                if snap["revision"] != last:
                    value = session(sid)
                    await ws.send_json(
                        {
                            "type": "state",
                            "revision": snap["revision"],
                            "session": value if access else participant_view(value),
                        }
                    )
                    last = snap["revision"]
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, asyncio.TimeoutError, HTTPException):
            pass

    @app.post("/api/sessions/{sid}/scene")
    def save_scene(sid: str, body: dict, request: Request):
        therapist(request)
        image, raw = decode_image(body.get("image", ""))
        import io
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        raw = normalized.getvalue()
        directory = cfg.work / "scenes"
        directory.mkdir(exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        filename = hashlib.sha256(sid.encode()).hexdigest() + "-" + digest + ".png"
        path = directory / filename
        if not path.exists():
            path.write_bytes(raw)

        def apply(s):
            if s["status"] == "completed":
                raise ValueError("Session completed")
            s["scene_file"] = filename
            s["source_hash"] = digest
            s.pop("spatialDecision", None)
            s["media"] = {
                "kind": "image",
                "source": "desktop_snapshot",
                "url": f"/api/sessions/{sid}/scene?v={digest}",
                "region_map_verified": True,
            }

        return store.mutate(sid, apply)

    @app.post("/api/sessions/{sid}/transition-complete")
    def transition_complete(sid: str, body: dict, request: Request):
        role(request, sid)
        def apply(s):
            active = s.get("media", {})
            if s["status"] != "active" or body.get("job_id") != active.get("job_id") or not active.get("entry"):
                raise ValueError("Stale transition")
            job = next(j for j in store.jobs(sid) if j["id"] == active["job_id"])
            if s.get("source_hash") == active["final_hash"]:
                return
            directory = cfg.work / "scenes"
            directory.mkdir(exist_ok=True)
            filename = active["final_hash"] + ".png"
            (directory / filename).write_bytes((cfg.work / "media" / job["id"] / "final.png").read_bytes())
            s["scene_file"] = filename
            s["source_hash"] = active["final_hash"]
            s["cycle"] += 1
            s["remaining"] = 30
            s["pendingCycle"] = False
            s.pop("spatialDecision", None)
            event(s, "cycle", "Region entry completed; final frame is next source")
        return store.mutate(sid, apply)

    @app.get("/api/sessions/{sid}/scene")
    def get_scene(sid: str, request: Request):
        role(request, sid)
        filename = session(sid).get("scene_file", "")
        path = cfg.work / "scenes" / filename
        if not path.is_file():
            raise HTTPException(404, "Scene not uploaded yet")
        return FileResponse(path, media_type="image/png")

    @app.post("/api/sessions/{sid}/canonical-scene")
    def canonical_scene(sid: str, request: Request):
        import base64
        import io
        from PIL import Image
        therapist(request)
        path = cfg.root / "Assets" / "Images" / "ideal_abstract.jpeg"
        if not path.is_file():
            raise ValueError("Canonical image is unavailable")
        buffer = io.BytesIO()
        with Image.open(path) as image:
            image.convert("RGB").save(buffer, format="PNG")
        return save_scene(sid, {"image": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()}, request)

    @app.post("/api/sessions/{sid}/region-entry")
    async def region_entry(sid: str, body: EntryBody, request: Request):
        import base64
        from .region_zoom import visual_brief
        therapist(request)
        value = session(sid)
        selected = value.get("spatialDecision")
        if value["status"] != "active" or not selected or selected["cycle"] != value["cycle"] or selected["source_hash"] != value.get("source_hash"):
            raise ValueError("Freeze a current spatial decision first")
        brief = visual_brief(body.excerpt)
        jobs = store.jobs(sid)
        if body.parent_job:
            parent = next((j for j in jobs if j["id"] == body.parent_job), None)
            if not parent or parent["status"] != "ready" or parent["kind"] != "image" or parent.get("entry") != selected:
                raise ValueError("A ready start image for this decision is required")
            if any(j.get("parent_job") == parent["id"] for j in jobs):
                raise ValueError("Video already submitted; reconcile existing job")
            path = cfg.work / "media" / parent["id"] / parent["output_path"]
            kind = "video"
            brief = parent["brief"]
        else:
            if any(j.get("entry") == selected and j["kind"] == "image" for j in jobs):
                raise ValueError("Start image already submitted; reconcile existing job")
            from .region_zoom import billable_units
            if billable_units(jobs) + 3 > cfg.max_jobs:
                raise ValueError("Region entry requires three available provider calls")
            path = cfg.work / "scenes" / value.get("scene_file", "")
            kind = "image"
        if not path.is_file():
            raise ValueError("Current source image is unavailable")
        data = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
        job = await media.submit(value, data, brief, kind, entry=selected)
        if body.parent_job:
            job["parent_job"] = body.parent_job
            media.persist(job)
        return job

    @app.get("/api/sessions/{sid}/media/{jid}/frame/{frame}")
    def media_frame(sid: str, jid: str, frame: str, request: Request):
        role(request, sid)
        job = next((j for j in store.jobs(sid) if j["id"] == jid), None)
        if not job or job["status"] != "ready" or frame not in ("first", "final") or not job.get("frame_hashes"):
            raise HTTPException(404, "No validated frame")
        return FileResponse(cfg.work / "media" / jid / (frame + ".png"), media_type="image/png")

    @app.post("/api/sessions/{sid}/media")
    async def make_media(sid: str, body: MediaBody, request: Request):
        therapist(request)
        value = session(sid)
        if value["status"] != "active":
            raise HTTPException(409, "Resume before creating media")
        return await media.submit(value, body.image, body.brief, body.kind)

    @app.get("/api/sessions/{sid}/media")
    def list_media(sid: str, request: Request):
        therapist(request)
        return store.jobs(sid)

    @app.get("/api/sessions/{sid}/media/{jid}/artifact")
    def artifact(sid: str, jid: str, request: Request):
        role(request, sid)
        job = next((j for j in store.jobs(sid) if j["id"] == jid), None)
        if not job or job["status"] != "ready":
            raise HTTPException(404, "No validated artifact")
        return FileResponse(
            cfg.work / "media" / jid / job["output_path"],
            media_type="image/png" if job["kind"] == "image" else "video/mp4",
        )

    @app.post("/api/sessions/{sid}/media/apply")
    def apply_media(sid: str, body: ApplyBody, request: Request):
        therapist(request)
        job = next((j for j in store.jobs(sid) if j["id"] == body.job_id), None)
        if not job or job["status"] != "ready" or not body.continuity_confirmed:
            raise ValueError("Preview and confirm continuity before using media")

        def apply(s):
            if s["status"] != "active" or s["cycle"] != job["cycle"]:
                raise ValueError(
                    "Paused, completed or stale cycle; media was not applied"
                )
            if job.get("entry") and (job["kind"] != "video" or job["entry"] != s.get("spatialDecision")):
                raise ValueError("Approve a complete video bundle for the current decision")
            if s.get("media", {}).get("job_id") == job["id"]:
                return
            s["media"] = {
                "entry": bool(job.get("entry")),
                "first_url": f"/api/sessions/{sid}/media/{job['id']}/frame/first" if job.get("entry") else "",
                "final_url": f"/api/sessions/{sid}/media/{job['id']}/frame/final" if job.get("entry") else "",
                "final_resolution": job.get("final_resolution"),
                "final_hash": job.get("frame_hashes", {}).get("final.png", ""),
                "job_id": job["id"],
                "kind": job["kind"],
                "url": f"/api/sessions/{sid}/media/{job['id']}/artifact",
                "duration": job.get("validation", {}).get("duration_seconds"),
                "region_map_verified": True,
            }
            event(
                s,
                "media",
                "Practitioner approved "
                + job["kind"]
                + " continuity and region mapping",
            )

        result = store.mutate(sid, apply)
        job["region_map_verified"] = True
        media.persist(job)
        return result

    @app.websocket("/api/sessions/{sid}/voice")
    async def voice_proxy(ws: WebSocket, sid: str):
        reserved = False
        await ws.accept()
        try:
            origin = ws.headers.get("origin")
            if origin and urlparse(origin).netloc != ws.headers.get("host"):
                await ws.close(4403)
                return
            auth = await asyncio.wait_for(ws.receive_json(), timeout=10)
            if (
                not secrets.compare_digest(
                    ws.cookies.get("landscape_admin", ""), admin_token
                )
                and store.token_session(auth.get("token", "")) != sid
            ):
                await ws.close(4401)
                return
            if not auth.get("consent"):
                await ws.close(4403)
                return
            if session(sid)["status"] != "active":
                await ws.close(4409)
                return
            if sid in active_voice:
                await ws.send_json(
                    {
                        "type": "error",
                        "message": "A voice connection is already active for this session",
                    }
                )
                return
            active_voice.add(sid)
            reserved = True
            url = await asyncio.to_thread(voice.signed_url)
            async with websockets.connect(url, max_size=2_000_000) as upstream:
                await upstream.send(
                    json.dumps({"type": "conversation_initiation_client_data"})
                )

                async def to_provider():
                    while True:
                        item = await ws.receive_json()
                        if session(sid)["status"] != "active":
                            return
                        if (
                            set(item) == {"user_audio_chunk"}
                            and isinstance(item["user_audio_chunk"], str)
                            and len(item["user_audio_chunk"]) < 100000
                        ):
                            await upstream.send(json.dumps(item))
                        elif item.get("type") == "context_request":
                            s = session(sid)
                            context = {
                                "region": s["region"],
                                "cycle": s["cycle"],
                                "depth": s["depth"],
                                "attention": s.get("attention", {}),
                                "excluded_topics": s["exclusions"],
                            }
                            await upstream.send(
                                json.dumps(
                                    {
                                        "type": "contextual_update",
                                        "text": json.dumps(context),
                                    }
                                )
                            )

                async def from_provider():
                    async for raw in upstream:
                        item = json.loads(raw)
                        if item.get("type") == "ping":
                            await upstream.send(
                                json.dumps(
                                    {
                                        "type": "pong",
                                        "event_id": item["ping_event"]["event_id"],
                                    }
                                )
                            )
                            continue
                        if session(sid)["status"] != "active":
                            return
                        from .voice_events import transcript
                        turn = transcript(item)
                        if turn:
                            kind, text = turn
                            store.mutate(sid, lambda s: event(s, kind, text, "elevenlabs", region=s["region"]))
                        if item.get("type") in (
                            "audio",
                            "interruption",
                            "user_transcript",
                            "agent_response",
                            "conversation_initiation_metadata",
                        ):
                            await ws.send_json(item)

                async def watch_session():
                    previous = None
                    while session(sid)["status"] == "active":
                        s = session(sid)
                        context = {
                            "region": s["region"],
                            "cycle": s["cycle"],
                            "depth": s["depth"],
                            "attention": s.get("attention", {}),
                            "excluded_topics": s["exclusions"],
                        }
                        text = json.dumps(context)
                        if text != previous:
                            await upstream.send(
                                json.dumps({"type": "contextual_update", "text": text})
                            )
                            previous = text
                        await asyncio.sleep(2)

                tasks = [
                    asyncio.create_task(c())
                    for c in (to_provider, from_provider, watch_session)
                ]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for t in tasks:
                        t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except ProviderUnavailable as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        except Exception:
            try:
                await ws.send_json(
                    {
                        "type": "error",
                        "message": "Voice connection ended. Keep the session paused or continue without voice.",
                    }
                )
            except RuntimeError:
                pass
        finally:
            if reserved:
                active_voice.discard(sid)
            try:
                await ws.close()
            except (WebSocketDisconnect, RuntimeError):
                pass

    app.mount(
        "/", StaticFiles(directory=cfg.root / "frontend", html=True), name="frontend"
    )
    return app
