import base64
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from inner_landscape.api import create_app
from inner_landscape.config import Settings
from inner_landscape.domain import command, participant_view, propose
from inner_landscape.providers import decode_image, region_box, trusted_media_url


def fixture():
    return {
        "id": "session-test",
        "clientId": "demo-jamie",
        "createdAt": "2026-10-24T08:00:00Z",
        "completedAt": None,
        "status": "active",
        "goal": "Notice the landscape",
        "preNotes": "PRIVATE BEFORE",
        "postNotes": "PRIVATE AFTER",
        "exclusions": "no water",
        "before": "4",
        "after": "",
        "depth": {"sky": 0, "ridge": 0, "water": 0},
        "region": "ridge",
        "remaining": 30,
        "cycle": 1,
        "pendingCycle": False,
        "approved": False,
        "events": [
            {
                "type": "guide",
                "text": "What draws you in?",
                "at": "2026-10-24T08:00:00Z",
            },
            {
                "type": "note",
                "text": "PRIVATE OBSERVATION",
                "at": "2026-10-24T08:00:00Z",
            },
        ],
    }


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "frontend").mkdir()
        (root / "frontend/index.html").write_text("<h1>Demo</h1>")
        self.app = create_app(Settings(root=root))
        self.client = TestClient(self.app)
        self.client.get("/")
        first = self.client.get("/api/workspace").json()
        self.ws = {
            "version": 1,
            "sessions": [fixture()],
            "notes": {"demo-jamie": "PRIVATE PROFILE"},
        }
        result = self.client.put(
            "/api/workspace", json={"revision": first["revision"], "workspace": self.ws}
        )
        self.assertEqual(result.status_code, 200)
        self.rev = result.json()["revision"]

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def participant(self):
        code = self.client.post("/api/sessions/session-test/pair").json()["code"]
        guest = TestClient(self.app)
        paired = guest.post("/api/pair", json={"code": code})
        self.assertEqual(paired.status_code, 200)
        return guest, {"Authorization": "Bearer " + paired.json()["token"]}, code

    def test_private_data_and_provider_keys_are_not_public(self):
        guest, headers, code = self.participant()
        self.assertEqual(guest.get("/api/workspace").status_code, 401)
        self.assertEqual(guest.get("/api/status").status_code, 401)
        response = guest.get("/api/sessions/session-test", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("PRIVATE", response.text)
        self.assertNotIn("exclusions", response.json())
        self.assertEqual(guest.post("/api/pair", json={"code": code}).status_code, 401)
        self.assertEqual(
            guest.get("/api/sessions/other", headers=headers).status_code, 401
        )
        guest.close()

    def test_workspace_optimistic_concurrency_and_validation(self):
        self.assertEqual(
            self.client.put(
                "/api/workspace", json={"revision": self.rev - 1, "workspace": self.ws}
            ).status_code,
            409,
        )
        bad = copy.deepcopy(self.ws)
        bad["sessions"][0]["depth"]["sky"] = 10
        self.assertEqual(
            self.client.put(
                "/api/workspace", json={"revision": self.rev, "workspace": bad}
            ).status_code,
            422,
        )

    def test_cross_origin_mutation_is_rejected(self):
        self.assertEqual(
            self.client.post(
                "/api/sessions/session-test/pair",
                headers={"Origin": "https://other.example"},
            ).status_code,
            403,
        )

    def test_participant_commands_are_deduplicated_and_cannot_resume(self):
        guest, headers, _ = self.participant()
        body = {"command_id": "command-0001", "command": "pause", "payload": {}}
        first = guest.post(
            "/api/sessions/session-test/commands", json=body, headers=headers
        )
        second = guest.post(
            "/api/sessions/session-test/commands", json=body, headers=headers
        )
        self.assertEqual(first.json(), second.json())
        self.assertEqual(first.json()["session"]["status"], "paused")
        body.update(command="resume", command_id="command-0002")
        self.assertEqual(
            guest.post(
                "/api/sessions/session-test/commands", json=body, headers=headers
            ).status_code,
            403,
        )
        guest.close()

    def test_attention_cycle_validation_and_tracking_loss(self):
        s = fixture()
        with self.assertRaises(ValueError):
            command(s, "attention", {"cycle": 0, "dwell": {"sky": 2}}, "participant")
        command(
            s, "attention", {"cycle": 1, "dwell": {"sky": 5, "ridge": 1}}, "participant"
        )
        self.assertEqual(s["proposal"]["region"], "sky")
        self.assertTrue(s["proposal"]["requires_confirmation"])
        self.assertEqual(s["region"], "ridge")  # recommendation never applies itself
        command(s, "tracking_lost", {}, "participant")
        self.assertEqual(s["status"], "paused")
        self.assertEqual(s["attention"], {})

    def test_completed_session_rejects_commands(self):
        s = fixture()
        command(s, "stop", {}, "therapist")
        with self.assertRaises(ValueError):
            command(s, "resume", {}, "therapist")

    def test_paid_media_gate_submits_nothing(self):
        response = self.client.post(
            "/api/sessions/session-test/media",
            json={
                "image": "data:image/png;base64,AAAA",
                "brief": "soft clouds",
                "kind": "image",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.app.state.store.jobs("session-test"), [])

    def test_session_database_survives_restart_and_pauses(self):
        other = create_app(Settings(root=Path(self.temp.name)))
        s = other.state.store.read()["workspace"]["sessions"][0]
        self.assertEqual(s["preNotes"], "PRIVATE BEFORE")
        self.assertEqual(s["status"], "paused")

    def test_scene_requires_auth_and_keeps_provider_off(self):
        image = Image.new("RGB", (192, 128), "green")
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        encoded = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        result = self.client.post(
            "/api/sessions/session-test/scene", json={"image": encoded}
        )
        self.assertEqual(result.status_code, 200)
        guest, headers, _ = self.participant()
        self.assertEqual(
            guest.get("/api/sessions/session-test/scene", headers=headers).status_code,
            200,
        )
        self.assertEqual(guest.get("/api/sessions/session-test/scene").status_code, 401)
        guest.close()

    def test_stale_or_unapproved_media_cannot_apply(self):
        store = self.app.state.store
        job = {
            "id": "job-a",
            "session_id": "session-test",
            "cycle": 0,
            "status": "ready",
            "kind": "image",
        }
        store.put_job(job)
        for confirm in (False, True):
            r = self.client.post(
                "/api/sessions/session-test/media/apply",
                json={"job_id": "job-a", "continuity_confirmed": confirm},
            )
            self.assertEqual(r.status_code, 422)

    def test_voice_paid_gate_without_microphone_or_provider_call(self):
        with self.client.websocket_connect("/api/sessions/session-test/voice") as ws:
            ws.send_json({"consent": True})
            result = ws.receive_json()
            self.assertEqual(result["type"], "error")
            self.assertIn("disabled", result["message"])

    def test_stale_attention_and_explicit_exclusions_do_not_drive_proposal(self):
        s = fixture()
        s["attention"] = {"water": 20}
        s["attentionAt"] = "2000-01-01T00:00:00+00:00"
        self.assertEqual(propose(s)["region"], "ridge")
        s["attentionAt"] = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat()
        )
        self.assertNotEqual(propose(s)["region"], "water")

    def test_environment_files_are_not_served(self):
        self.assertEqual(self.client.get("/.env").status_code, 404)
        self.assertEqual(self.client.get("/.env.local").status_code, 404)


class ImageTests(unittest.TestCase):
    def test_real_png_decode_and_crop_preserve_original(self):
        original = Image.new("RGB", (300, 100), (7, 23, 47))
        buffer = io.BytesIO()
        original.save(buffer, format="PNG")
        image, raw = decode_image(
            "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        )
        box = region_box(image.size, "ridge")
        copy = image.copy()
        copy.paste(Image.new("RGB", (100, 100), "white"), box)
        self.assertEqual(copy.getpixel((10, 20)), (7, 23, 47))
        self.assertEqual(copy.getpixel((250, 20)), (7, 23, 47))
        self.assertEqual(image.getpixel((150, 20)), (7, 23, 47))
        self.assertEqual(raw, buffer.getvalue())

    def test_invalid_images_and_untrusted_urls_rejected(self):
        with self.assertRaises(ValueError):
            decode_image("data:image/jpeg;base64,AAAA")
        self.assertFalse(trusted_media_url("http://127.0.0.1/private"))
        self.assertFalse(trusted_media_url("https://fal.media.evil.example/file"))
        self.assertTrue(trusted_media_url("https://v3.fal.media/file.png"))


if __name__ == "__main__":
    unittest.main()
