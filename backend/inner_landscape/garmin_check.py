"""Bounded hardware smoke check: discovery alone never counts as a broadcast pass."""
from __future__ import annotations

import argparse
import asyncio
import json
import time

from .garmin import HeartRateMonitor
from .garmin_ble import GarminBLE


async def check_broadcast(name: str = "venu", seconds: int = 15, bridge=None):
    bridge = bridge or GarminBLE(HeartRateMonitor())
    try:
        found = (await bridge.scan())["devices"]
        matches = [d for d in found if name.lower() in d["name"].lower()]
        if len(matches) != 1:
            return {"passed": False, "reason": "No unique matching watch. Enable broadcasting or use --name to select one.", "matching_devices": len(matches)}
        lease = await bridge.start("broadcast-check", matches[0]["id"])
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            observation = bridge.view("broadcast-check", lease["token"])
            if observation.get("bpm") is not None:
                return {"passed": True, "reason": "Received a valid GATT heart-rate notification.", "bpm": observation["bpm"]}
            if bridge.task.done():
                break
            await asyncio.sleep(.1)
        return {"passed": False, "reason": "No valid heart-rate notification received before timeout."}
    finally:
        await bridge.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="venu", help="Unique device-name substring")
    parser.add_argument("--seconds", type=int, choices=range(3,31), default=15, metavar="3..30")
    args = parser.parse_args()
    try:
        result = asyncio.run(check_broadcast(args.name, args.seconds))
    except Exception as error:
        result = {"passed": False, "reason": str(error)}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
