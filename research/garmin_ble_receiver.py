"""Garmin BLE Heart Rate Receiver & Logger for Inner Landscape.

Connects to a Garmin watch (e.g. Venu 4) broadcasting Heart Rate over standard
Bluetooth Low Energy GATT (Service 0x180D, Measurement 0x2A37).

Saves structured session runs conforming to research/README.md:
  - runs/garmin/<run_id>/heart-rate.csv
  - runs/garmin/<run_id>/events.csv
  - runs/garmin/<run_id>/manifest.json

Requirements:
  bleak (run via `uv run --with bleak python research/garmin_ble_receiver.py`)
"""

import argparse
import asyncio
import csv
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Reuse the same parser as the coordinator; the CLI keeps its existing logging flow.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from inner_landscape.garmin_protocol import parse_hr_payload, is_hr_match

RECEIVER_VERSION = "0.1.0"
HR_SERVICE_16 = "180d"
HR_SERVICE_128 = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"


class GarminReceiverSession:
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        save_run: bool = True,
    ):
        self.save_run = save_run
        self.run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = output_dir or (Path("runs") / "garmin" / self.run_id)
        self.start_utc: Optional[str] = None
        self.start_mono: Optional[float] = None
        self.sample_count = 0
        self.events: List[Dict[str, Any]] = []
        self.device_info: Dict[str, Any] = {}
        self._hr_writer: Optional[csv.writer] = None
        self._hr_file = None
        self._events_writer: Optional[csv.writer] = None
        self._events_file = None

    def start_logging(self, device: BLEDevice) -> None:
        self.device_info = {
            "name": device.name or "Unknown",
            "address": device.address,
        }
        self.start_utc = datetime.now(timezone.utc).isoformat()
        self.start_mono = time.monotonic()

        if self.save_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._hr_file = open(self.output_dir / "heart-rate.csv", "w", newline="", encoding="utf-8")
            self._hr_writer = csv.writer(self._hr_file)
            self._hr_writer.writerow(["utc_time", "elapsed_seconds", "bpm", "contact_detected", "rr_ms"])

            self._events_file = open(self.output_dir / "events.csv", "w", newline="", encoding="utf-8")
            self._events_writer = csv.writer(self._events_file)
            self._events_writer.writerow(["utc_time", "elapsed_seconds", "event_type", "details"])

        self.log_event("session_start", f"Run {self.run_id} started for {self.device_info['name']}")

    def log_event(self, event_type: str, details: str = "") -> None:
        now_utc = datetime.now(timezone.utc).isoformat()
        elapsed = round(time.monotonic() - self.start_mono, 3) if self.start_mono else 0.0
        self.events.append({"utc_time": now_utc, "elapsed_seconds": elapsed, "type": event_type, "details": details})
        if self._events_writer and self._events_file:
            self._events_writer.writerow([now_utc, elapsed, event_type, details])
            self._events_file.flush()

    def record_measurement(
        self,
        bpm: int,
        contact_detected: Optional[bool],
        rr_intervals: List[float],
    ) -> None:
        self.sample_count += 1
        now_utc = datetime.now(timezone.utc).isoformat()
        elapsed = round(time.monotonic() - (self.start_mono or time.monotonic()), 3)
        rr_str = ";".join(f"{ms:.1f}" for ms in rr_intervals) if rr_intervals else ""
        contact_val = "" if contact_detected is None else ("1" if contact_detected else "0")

        if self._hr_writer and self._hr_file:
            self._hr_writer.writerow([now_utc, elapsed, bpm, contact_val, rr_str])
            self._hr_file.flush()

    def finish(self, status: str = "completed") -> None:
        self.log_event("session_end", f"Status: {status}, Samples: {self.sample_count}")
        if self._hr_file:
            self._hr_file.close()
        if self._events_file:
            self._events_file.close()

        if self.save_run:
            manifest = {
                "manifest_version": "1.0",
                "receiver_version": RECEIVER_VERSION,
                "run_id": self.run_id,
                "status": status,
                "start_utc": self.start_utc,
                "end_utc": datetime.now(timezone.utc).isoformat(),
                "device": self.device_info,
                "sample_count": self.sample_count,
                "outputs": {
                    "heart_rate_csv": str(self.output_dir / "heart-rate.csv"),
                    "events_csv": str(self.output_dir / "events.csv"),
                },
            }
            manifest_path = self.output_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            print(f"\n[Session saved] Output written to {self.output_dir}/")




async def run_scan_only(timeout: float) -> None:
    print(f"Scanning for {timeout}s for all Bluetooth LE devices...")
    found: List[BLEDevice] = []

    def on_detect(device: BLEDevice, ad: AdvertisementData) -> None:
        services = [s.lower() for s in (ad.service_uuids or [])]
        name = device.name or ad.local_name or "Unknown"
        is_hr = any(s in (HR_SERVICE_16, HR_SERVICE_128) or s.startswith("0000180d") for s in services)
        is_garmin = "garmin" in name.lower() or "venu" in name.lower()
        marker = " [★ HR SERVICE]" if is_hr else (" [Garmin Device]" if is_garmin else "")
        print(f"  {name} [{device.address}] RSSI: {ad.rssi} dBm{marker}")
        found.append(device)

    scanner = BleakScanner(detection_callback=on_detect)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    print(f"\nScan complete. Discovered {len(found)} devices.")


async def run_receiver(
    timeout: float,
    device_filter: Optional[str] = None,
    save_run: bool = True,
) -> None:
    session = GarminReceiverSession(save_run=save_run)

    def hr_filter(device: BLEDevice, ad: AdvertisementData) -> bool:
        if device_filter:
            target = device_filter.lower()
            addr = device.address.lower()
            name = (device.name or ad.local_name or "").lower()
            if target not in addr and target not in name:
                return False
        return is_hr_match(device, ad)

    print(f"Scanning for Garmin / HR broadcasting device (timeout: {timeout}s)...")
    device = await BleakScanner.find_device_by_filter(hr_filter, timeout=timeout)

    if not device:
        print("\nDevice not found within timeout.")
        print("Checklist:")
        print("  1. Make sure 'Broadcast Heart Rate' is actively running on the watch.")
        print("  2. Watch must be on your wrist with heart rate detected.")
        print("  3. Keep the watch within 2 meters of your Mac.")
        print("  4. Run with --scan-only to inspect all visible BLE devices.")
        return

    name = device.name or "Garmin HR Device"
    print(f"\nFound device: {name} [{device.address}]")
    session.start_logging(device)

    stop_event = asyncio.Event()

    def on_disconnect(client: BleakClient) -> None:
        print(f"\n[Disconnected] Lost connection to {name}.")
        session.log_event("disconnect", "Watch disconnected or broadcast ended")
        stop_event.set()

    def on_notification(sender: Any, data: bytearray) -> None:
        parsed = parse_hr_payload(data)
        if "error" in parsed:
            print(f"Warning: {parsed['error']}")
            return

        bpm = parsed["bpm"]
        contact = parsed["contact_detected"]
        rr_ms = parsed["rr_intervals_ms"]

        contact_badge = ""
        if contact is not None:
            contact_badge = f" [Contact: {'OK' if contact else 'Poor'}]"

        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] {name} Live HR: {bpm:3d} BPM{contact_badge}", end="")

        if rr_ms:
            print(f" | RR: {', '.join(f'{x:.0f}ms' for x in rr_ms)}")
        else:
            print()

        session.record_measurement(bpm=bpm, contact_detected=contact, rr_intervals=rr_ms)

    try:
        async with BleakClient(device, disconnected_callback=on_disconnect) as client:
            print(f"Connected to {name}. Subscribing to Heart Rate notifications...")
            session.log_event("connected", f"Address: {device.address}")
            await client.start_notify(HR_MEASUREMENT_UUID, on_notification)
            session.log_event("subscribed", f"UUID: {HR_MEASUREMENT_UUID}")
            print("Receiving live heart rate. Press Ctrl+C to stop session.\n" + "-" * 50)

            await stop_event.wait()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\nConnection error: {e}")
        session.log_event("error", str(e))
    finally:
        session.finish(status="completed" if session.sample_count > 0 else "aborted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Garmin BLE Heart Rate Receiver & Session Logger")
    parser.add_argument("--timeout", type=float, default=20.0, help="Scan timeout in seconds (default: 20)")
    parser.add_argument("--device", type=str, default=None, help="Specific device name or address to target")
    parser.add_argument("--no-save", action="store_true", help="Display only; do not save files to runs/garmin/")
    parser.add_argument("--scan-only", action="store_true", help="Scan and list nearby BLE devices without connecting")

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_sigint(*_: Any) -> None:
        print("\nStopping...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        if args.scan_only:
            loop.run_until_complete(run_scan_only(args.timeout))
        else:
            loop.run_until_complete(
                run_receiver(
                    timeout=args.timeout,
                    device_filter=args.device,
                    save_run=not args.no_save,
                )
            )
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
