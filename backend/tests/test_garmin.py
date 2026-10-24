import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from inner_landscape.api import create_app
from inner_landscape.config import Settings
from inner_landscape.garmin import HeartRateMonitor
from inner_landscape.garmin_ble import GarminBLE
from inner_landscape.garmin_check import check_broadcast
from inner_landscape.garmin_protocol import parse_hr_payload
from test_service import fixture


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.time = 0.0
        self.monitor = HeartRateMonitor(lambda: self.time)
        self.token = self.monitor.start("s")["token"]

    def sample(self, t, bpm=80):
        self.time = t
        return self.monitor.sample("s", self.token, bpm)

    def baseline(self):
        for t in range(31):
            self.sample(t)
        self.assertEqual(self.monitor.view("s")["baseline"], 80)

    def test_sustained_rise_recovery_and_single_outlier(self):
        self.baseline()
        self.assertFalse(self.sample(31, 120)["spike"])
        self.assertFalse(self.sample(32, 80)["spike"])
        for t in range(33, 38):
            self.assertFalse(self.sample(t, 100)["spike"])
        self.assertTrue(self.sample(38, 100)["spike"])
        for t in range(39, 45):
            result = self.sample(t, 80)
        self.assertFalse(result["spike"])

    def test_gap_clears_baseline_and_expiry_clears_lease(self):
        self.baseline()
        self.time = 40
        self.assertEqual(self.monitor.view("s")["status"], "stale")
        self.assertIsNone(self.monitor.view("s")["bpm"])
        self.assertIsNone(self.sample(41, 120)["baseline"])
        self.time = 71
        self.assertEqual(self.monitor.view("s")["status"], "disconnected")
        self.assertIsNone(self.monitor.token)

    def test_invalid_samples_and_ownership(self):
        for value in (True, 0, 241, float('nan'), "80"):
            with self.assertRaises(ValueError): self.sample(1, value)
        with self.assertRaises(ValueError): self.monitor.sample("s", "wrong", 80)
        with self.assertRaises(ValueError): self.monitor.start("other")
        self.monitor.reconcile(set())
        self.assertIsNone(self.monitor.token)

    def test_baseline_requires_duration_and_samples(self):
        for t in (0, 8, 16, 24, 32): self.sample(t)
        self.assertIsNone(self.monitor.view("s")["baseline"])

    def test_payload_optional_fields_and_truncation(self):
        self.assertEqual(parse_hr_payload(bytearray([0, 80]))["bpm"], 80)
        result = parse_hr_payload(bytearray([0x1f, 80, 0, 1, 0, 0, 4]))
        self.assertTrue(result["contact_detected"])
        self.assertEqual(result["rr_intervals_ms"], [1000])
        for payload in ([], [1, 80], [8, 80], [16, 80], [16, 80, 1]):
            self.assertIn("error", parse_hr_payload(bytearray(payload)))


class FakeClient:
    instances = []
    fail = False
    def __init__(self, device, disconnected_callback):
        self.disconnected = False
        self.callback = disconnected_callback
        self.notification = None
        self.instances.append(self)
    async def connect(self):
        if self.fail: raise RuntimeError("synthetic failure")
    async def start_notify(self, uuid, callback):
        self.notification = callback
        callback(None, bytearray([0, 80]))
    async def disconnect(self): self.disconnected = True


class FakeScanner:
    @staticmethod
    async def discover(**kwargs):
        return {"x": (SimpleNamespace(name="Venu test"), SimpleNamespace(service_uuids=["180d"], local_name="Venu test"))}


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_sample_disconnect_and_failure(self):
        m = HeartRateMonitor()
        bridge = GarminBLE(m, FakeScanner, FakeClient)
        choice = (await bridge.scan())["devices"][0]["id"]
        result = await bridge.start("s", choice)
        for _ in range(5): await asyncio.sleep(0)
        self.assertEqual(bridge.view("s", result["token"])["bpm"], 80)
        await bridge.stop()
        self.assertTrue(FakeClient.instances[-1].disconnected)
        self.assertIsNone(m.token)
        self.assertFalse(bridge.devices)
        FakeClient.fail = True
        try:
            choice = (await bridge.scan())["devices"][0]["id"]
            await bridge.start("s", choice)
            await bridge.task
            self.assertIsNotNone(bridge.error)
            self.assertIsNone(m.sid)
            self.assertTrue(FakeClient.instances[-1].disconnected)
        finally: FakeClient.fail = False

    async def test_lost_browser_expires_and_disconnects(self):
        m = HeartRateMonitor()
        bridge = GarminBLE(m, FakeScanner, FakeClient)
        choice = (await bridge.scan())["devices"][0]["id"]
        await bridge.start("s", choice)
        bridge.heartbeat = time.monotonic() - 16
        await asyncio.wait_for(bridge.task, 1)
        self.assertIsNone(m.token)
        self.assertTrue(FakeClient.instances[-1].disconnected)


class GarminAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "frontend").mkdir()
        (root / "frontend/index.html").write_text("demo")
        self.app = create_app(Settings(root=root))
        self.app.state.garmin.scanner = FakeScanner
        self.app.state.garmin.client_factory = FakeClient
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.client.get("/")
        snap = self.client.get("/api/workspace").json()
        self.client.put("/api/workspace", json={"revision":snap["revision"], "workspace":{"version":1,"sessions":[fixture()],"notes":{}}})
        self.path = "/api/sessions/session-test/heart-rate"

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def connect(self):
        choice = self.client.post("/api/garmin/scan").json()["devices"][0]["id"]
        # Normal frontend saves between scan and connect must retain selection.
        snap = self.client.get("/api/workspace").json()
        self.client.put("/api/workspace", json=snap)
        result = self.client.post(self.path+"/start", json={"device_id":choice,"consent":True})
        self.assertEqual(result.status_code, 200)
        return {"X-Garmin-Token":result.json()["token"]}

    def test_auth_consent_and_no_workspace_persistence(self):
        guest = TestClient(self.app)
        self.assertEqual(guest.post("/api/garmin/scan").status_code,401)
        self.assertEqual(guest.get(self.path).status_code,401)
        self.assertEqual(self.client.post(self.path+"/start", json={"device_id":"x"}).status_code,422)
        self.assertEqual(self.client.post("/api/garmin/scan",headers={"Origin":"https://other.example"}).status_code,403)
        headers = self.connect()
        self.assertEqual(self.client.get(self.path,headers=headers).json()["bpm"],80)
        self.assertNotIn('"bpm"',self.client.get("/api/workspace").text)
        self.assertEqual(self.client.post(self.path+"/stop",headers={"X-Garmin-Token":"wrong"}).status_code,422)
        self.assertEqual(self.client.post(self.path+"/stop",headers=headers).status_code,200)
        self.assertIsNone(self.app.state.heart_rate.token)
        guest.close()

    def test_finishing_disconnects_and_cannot_reconnect(self):
        self.connect()
        response = self.client.post("/api/sessions/session-test/commands",json={"command_id":"stop-test-0001","command":"stop","payload":{}})
        self.assertEqual(response.status_code,200)
        self.assertTrue(FakeClient.instances[-1].disconnected)
        self.assertIsNone(self.app.state.heart_rate.token)
        self.assertEqual(self.client.post(self.path+"/start",json={"device_id":"x","consent":True}).status_code,409)

    def test_workspace_pause_also_disconnects(self):
        self.connect()
        snap=self.client.get("/api/workspace").json()
        snap["workspace"]["sessions"][0]["status"]="paused"
        self.assertEqual(self.client.put("/api/workspace",json=snap).status_code,200)
        self.assertTrue(FakeClient.instances[-1].disconnected)
        self.assertIsNone(self.app.state.heart_rate.baseline)


class BroadcastCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_pass_requires_notification_and_releases_connection(self):
        bridge = GarminBLE(HeartRateMonitor(), FakeScanner, FakeClient)
        result = await check_broadcast("Venu", 1, bridge)
        self.assertTrue(result["passed"])
        self.assertEqual(result["bpm"], 80)
        self.assertTrue(FakeClient.instances[-1].disconnected)
        self.assertIsNone(bridge.monitor.token)

    async def test_advertisement_without_valid_notification_is_not_pass(self):
        class SilentClient(FakeClient):
            async def start_notify(self, uuid, callback):
                callback(None, bytearray([1]))  # truncated packet
                callback(None, bytearray([4, 80]))  # explicitly no skin contact
        bridge = GarminBLE(HeartRateMonitor(), FakeScanner, SilentClient)
        result = await check_broadcast("Venu", .1, bridge)
        self.assertFalse(result["passed"])
        self.assertTrue(FakeClient.instances[-1].disconnected)
        self.assertIsNone(bridge.monitor.token)
