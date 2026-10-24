"""Synthetic Garmin FIT files for the 4-minute guided demo.

Replaces the watch-to-Mac transfer for demonstrations: writes FIT files shaped
like the ones a watch would provide, runs garmin_session_summary.py on them
exactly as on real files, and exports the summary for the frontend demo.

Every value is invented. No watch, account or person is involved; files are
named SYNTHETIC_* and marked "Synthetic demo" with the development manufacturer.
Output is deterministic, so the committed frontend file can be regenerated.

Writes:
  - runs/garmin/demo_fit/SYNTHETIC_*.fit      the fake watch files (ignored)
  - runs/garmin/demo_summary/                 summary.json + manifest.json (ignored)
  - frontend/demo-garmin.js                   summary for the guided demo

Requirements:
  garmin-fit-sdk (run via
  `uv run --with garmin-fit-sdk==21.218.0 python research/make_demo_garmin_fit.py`)
"""

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from garmin_fit_sdk import Encoder, Profile

import garmin_session_summary

ROOT = Path(__file__).resolve().parents[1]
FIT_DIR = ROOT / "runs" / "garmin" / "demo_fit"
SUMMARY_DIR = ROOT / "runs" / "garmin" / "demo_summary"
FRONTEND_FILE = ROOT / "frontend" / "demo-garmin.js"

# Matches the guided demo: one 4-minute session, the night before it in sleep data.
START = datetime(2026, 10, 24, 13, 0, tzinfo=timezone.utc)
DURATION_SECONDS = 240
END = START + timedelta(seconds=DURATION_SECONDS)
NIGHT_START = datetime(2026, 10, 23, 21, 40, tzinfo=timezone.utc)
WAKE = datetime(2026, 10, 24, 5, 30, tzinfo=timezone.utc)

MESG = Profile["mesg_num"]


def fit_file(file_type: str, messages: List[Dict[str, Any]]) -> bytes:
    encoder = Encoder()
    encoder.write_mesg({
        "mesg_num": MESG["FILE_ID"],
        "type": file_type,
        "manufacturer": "development",
        "product_name": "Synthetic demo",
        "time_created": START,
    })
    for mesg in messages:
        encoder.write_mesg(mesg)
    return encoder.close()


def heart_rate(second: int) -> int:
    # Gentle settling with small oscillation; illustrative, not modelled physiology.
    return round(74 - 6 * second / DURATION_SECONDS + 2 * math.sin(second / 9))


def respiration(second: int) -> float:
    return round(14.6 - 2.2 * second / DURATION_SECONDS + 0.4 * math.sin(second / 13), 2)


def activity() -> bytes:
    records = [
        {
            "mesg_num": MESG["RECORD"],
            "timestamp": START + timedelta(seconds=s),
            "heart_rate": heart_rate(s),
            "enhanced_respiration_rate": respiration(s),
        }
        for s in range(0, DURATION_SECONDS + 1)
    ]
    rates = [r["heart_rate"] for r in records]
    session = {
        "mesg_num": MESG["SESSION"],
        "timestamp": END,
        "start_time": START,
        "sport": "meditation",
        "sub_sport": "generic",
        "total_elapsed_time": DURATION_SECONDS,
        "total_timer_time": DURATION_SECONDS,
        "total_calories": 6,
        "avg_heart_rate": round(sum(rates) / len(rates)),
        "min_heart_rate": min(rates),
        "max_heart_rate": max(rates),
        "time_in_hr_zone": [DURATION_SECONDS, 0, 0, 0, 0],
        "total_training_effect": 0.1,
    }
    summary = {"mesg_num": MESG["ACTIVITY"], "timestamp": END, "num_sessions": 1, "total_timer_time": DURATION_SECONDS}
    return fit_file("activity", [*records, session, summary])


def monitoring() -> bytes:
    stress = [34, 33, 35, 31, 29, 28, 26, 25, 23]
    messages: List[Dict[str, Any]] = [
        {"mesg_num": MESG["STRESS_LEVEL"], "stress_level_time": START + timedelta(seconds=30 * i), "stress_level_value": v}
        for i, v in enumerate(stress)
    ]
    messages.append({
        "mesg_num": MESG["HSA_BODY_BATTERY_DATA"],
        "timestamp": START,
        "processing_interval": 60,
        "level": [58, 58, 59, 59, 60],
        "charged": [0, 0, 1, 0, 1],
        "uncharged": [0, 0, 0, 0, 0],
    })
    messages.append({
        "mesg_num": MESG["MONITORING_HR_DATA"],
        "timestamp": START - timedelta(hours=2),
        "resting_heart_rate": 61,
        "current_day_resting_heart_rate": 60,
    })
    return fit_file("monitoring_b", messages)


def sleep() -> bytes:
    stages = [
        (0, "awake"), (12, "light"), (45, "deep"), (110, "light"), (160, "rem"),
        (190, "light"), (240, "deep"), (285, "light"), (330, "rem"), (370, "awake"),
        (376, "light"), (420, "rem"), (470, "awake"),
    ]
    messages: List[Dict[str, Any]] = [
        {"mesg_num": MESG["SLEEP_LEVEL"], "timestamp": NIGHT_START + timedelta(minutes=m), "sleep_level": level}
        for m, level in stages
    ]
    messages.append({
        "mesg_num": MESG["SLEEP_ASSESSMENT"],
        "overall_sleep_score": 78,
        "sleep_quality_score": 74,
        "sleep_duration_score": 80,
        "deep_sleep_score": 70,
        "light_sleep_score": 85,
        "rem_sleep_score": 72,
        "sleep_recovery_score": 76,
        "awakenings_count": 2,
        "average_stress_during_sleep": 18,
    })
    messages.append({
        "mesg_num": MESG["SKIN_TEMP_OVERNIGHT"],
        "timestamp": WAKE,
        "average_deviation": -0.2,
        "average_7_day_deviation": 0.1,
    })
    messages.append({
        "mesg_num": MESG["HRV_STATUS_SUMMARY"],
        "timestamp": WAKE,
        "last_night_average": 46,
        "weekly_average": 44,
        "baseline_low_upper": 38,
        "baseline_balanced_lower": 40,
        "baseline_balanced_upper": 52,
        "status": "balanced",
    })
    return fit_file("monitoring_daily", messages)


def metrics() -> bytes:
    return fit_file("monitoring_daily", [{
        "mesg_num": MESG["MAX_MET_DATA"],
        "update_time": START - timedelta(days=4),
        "vo2_max": 41.0,
        "sport": "running",
        "sub_sport": "generic",
    }])


def write_frontend(summary: Dict[str, Any]) -> None:
    data = {"synthetic": True, "source": "Synthetic FIT files from research/make_demo_garmin_fit.py", **summary}
    FRONTEND_FILE.write_text(
        "/* Generated by research/make_demo_garmin_fit.py; do not edit by hand.\n"
        "   SIMULATED Garmin end-of-session summary for the guided demo: every value is\n"
        "   invented from synthetic FIT files. No watch or person was measured. */\n"
        "(function (root) {\n"
        '  "use strict";\n'
        f"  const summary = {json.dumps(data, indent=2)};\n"
        '  if (typeof module !== "undefined" && module.exports) module.exports = summary;\n'
        "  else root.LandscapeDemoGarmin = summary;\n"
        '})(typeof window !== "undefined" ? window : globalThis);\n',
        encoding="utf-8",
    )


def main() -> int:
    FIT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "SYNTHETIC_activity.fit": activity(),
        "SYNTHETIC_monitor.fit": monitoring(),
        "SYNTHETIC_sleep.fit": sleep(),
        "SYNTHETIC_metrics.fit": metrics(),
    }
    for name, data in files.items():
        (FIT_DIR / name).write_bytes(data)
        print(f"  wrote {name} ({len(data)} bytes)")

    status = garmin_session_summary.main([str(FIT_DIR), "--output-dir", str(SUMMARY_DIR), "--session-id", "guided-demo"])
    if status != 0:
        return status
    summary = json.loads((SUMMARY_DIR / "summary.json").read_text(encoding="utf-8"))
    write_frontend(summary)
    print(f"[Demo data] Frontend summary written to {FRONTEND_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
