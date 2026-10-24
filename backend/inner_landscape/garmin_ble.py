"""Mac BLE lifecycle adapted from research/garmin_ble_receiver.py (no recording)."""
from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any

from .garmin import HeartRateMonitor
from .garmin_protocol import HR_MEASUREMENT_UUID, is_hr_match, parse_hr_payload


class GarminBLE:
    def __init__(self, monitor: HeartRateMonitor, scanner=None, client_factory=None):
        self.monitor = monitor
        self.scanner = scanner
        self.client_factory = client_factory
        self.devices: dict[str, tuple[Any, float]] = {}
        self.task = None
        self.state = "disconnected"
        self.error = None
        self.heartbeat = 0.0
        self.lock = asyncio.Lock()

    def drivers(self):
        if self.scanner is None or self.client_factory is None:
            from bleak import BleakClient, BleakScanner
            self.scanner = self.scanner or BleakScanner
            self.client_factory = self.client_factory or BleakClient

    async def scan(self):
        async with self.lock:
            if self.task and not self.task.done():
                raise ValueError("Disconnect the watch before scanning again")
            self.drivers()
            try:
                found = await asyncio.wait_for(self.scanner.discover(timeout=8, return_adv=True), 12)
            except Exception:
                raise ValueError("Bluetooth scan failed. Enable Bluetooth and allow the coordinator's terminal/Python Bluetooth access in macOS settings.") from None
            self.devices.clear()
            result = []
            for device, ad in found.values():
                if is_hr_match(device, ad):
                    key = secrets.token_urlsafe(16)
                    self.devices[key] = device, time.monotonic()
                    result.append({"id": key, "name": (device.name or ad.local_name or "Heart-rate device")[:100]})
            return {"devices": result}

    async def start(self, sid: str, device_id: str):
        async with self.lock:
            if self.task and not self.task.done():
                raise ValueError("Heart-rate monitoring is already active")
            item = self.devices.get(device_id)
            if not item or time.monotonic() - item[1] > 60:
                raise ValueError("Watch selection expired; scan again")
            self.drivers()
            result = self.monitor.start(sid)
            self.devices.clear()
            self.heartbeat = time.monotonic()
            self.state, self.error = "connecting", None
            self.task = asyncio.create_task(self.receive(item[0], sid, result["token"]))
            return result

    async def receive(self, device, sid, token):
        lost = asyncio.Event()
        last_sample = -float("inf")
        def notification(_sender, payload):
            nonlocal last_sample
            parsed = parse_hr_payload(payload)
            if "error" in parsed or parsed.get("contact_detected") is False:
                return
            if time.monotonic() - last_sample < 0.9:
                return
            try:
                self.monitor.sample(sid, token, parsed["bpm"])
                last_sample = time.monotonic()
            except ValueError:
                pass
        try:
            # Explicit wait_for bounds connect even when BLEDevice avoids implicit scan.
            client = self.client_factory(device, disconnected_callback=lambda _: lost.set())
            try:
                await asyncio.wait_for(client.connect(), 15)
                await asyncio.wait_for(client.start_notify(HR_MEASUREMENT_UUID, notification), 5)
                self.state = "connected"
                while not lost.is_set():
                    if self.monitor.view(sid)["status"] == "disconnected" or time.monotonic() - self.heartbeat > 15:
                        break
                    await asyncio.sleep(0.5)
            finally:
                try:
                    await asyncio.wait_for(client.disconnect(), 5)
                except Exception:
                    self.error = "Bluetooth disconnect could not be confirmed; stop broadcasting on the watch."
        except asyncio.CancelledError:
            raise
        except Exception:
            self.error = "Watch connection failed or ended. Check Broadcast Heart Rate, close the standalone receiver, then scan and reconnect."
        finally:
            self.state = "disconnected"
            self.monitor.clear()
            self.devices.clear()

    def view(self, sid, token=""):
        if token and self.monitor.sid == sid and self.monitor.token and secrets.compare_digest(token, self.monitor.token):
            self.heartbeat = time.monotonic()
        result = self.monitor.view(sid)
        result["transport"] = self.state if self.monitor.sid == sid else "disconnected"
        result["error"] = self.error
        result["broadcast_received"] = result.get("bpm") is not None and result.get("status") != "stale"
        return result

    async def stop(self):
        async with self.lock:
            task, self.task = self.task, None
            if task and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            self.monitor.clear()
            self.devices.clear()
            self.state = "disconnected"
