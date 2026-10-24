"""Garmin end-of-session summary from local FIT files for Inner Landscape.

Stress, Body Battery, respiration, sleep, skin temperature, activity and fitness
metrics are not part of the live Bluetooth heart-rate broadcast. Instead, start
an activity recording on the watch when the session starts, stop and save it at
the end, sync the watch, and pass the resulting FIT files to this script:

  - the activity FIT file (Garmin Connect -> Export Original, or the watch's
    GARMIN/Activity folder over USB)
  - optionally the watch's monitoring, sleep and metrics FIT files (for example
    GARMIN/Monitor, GARMIN/Sleep, GARMIN/Metrics; folder names vary by model)

Saves a structured run under ignored runs/garmin/<run_id>/:
  - summary.json   metrics for the session window and the preceding night
  - manifest.json  inputs (with SHA-256), parameters, command, status, outputs

Metrics missing from the files are reported as not_available; nothing is
estimated or filled in. Values are Garmin's device measurements and estimates,
not emotional or clinical assessments.

Requirements:
  garmin-fit-sdk (run via
  `uv run --with garmin-fit-sdk==21.218.0 python research/garmin_session_summary.py`)
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

SUMMARY_VERSION = "0.1.0"
FIT_SDK_VERSION = "21.218.0"
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_FILES = 200
MAX_SESSION_HOURS = 12
DEFAULT_NIGHT_LOOKBACK_HOURS = 24
SLEEP_LEVELS = ("awake", "light", "deep", "rem", "unmeasurable")

Messages = Dict[str, List[Dict[str, Any]]]
Point = Tuple[datetime, float]

LIMITS = [
    "Values are Garmin device measurements and estimates, not emotional, "
    "diagnostic or clinical assessments.",
    "Stress is Garmin's heart-rate-variability-based estimate, not a measure of "
    "how the participant felt.",
    "Sleep, skin temperature and HRV status describe the night before the "
    "session, not the session itself.",
    "Metrics marked not_available were absent from the supplied files; which "
    "metrics a watch writes to FIT files depends on model and firmware.",
]


@dataclass
class FitInput:
    path: Path
    size_bytes: int = 0
    sha256: str = ""
    status: str = "pending"
    error: str = ""
    messages: Messages = field(default_factory=dict)

    def describe(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "status": self.status,
            "message_types": sorted(self.messages),
        }
        if self.error:
            info["error"] = self.error
        return info


# --- Input handling ---------------------------------------------------------


def parse_time(value: str) -> datetime:
    """Parses ISO 8601. Times without an offset are taken as this computer's local time."""
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


def collect_paths(values: List[str]) -> List[Path]:
    paths: List[Path] = []
    for value in values:
        path = Path(value).expanduser()
        if path.is_dir():
            paths.extend(p for p in sorted(path.rglob("*")) if p.is_file() and p.suffix.lower() == ".fit")
        elif path.is_file():
            paths.append(path)
        else:
            raise ValueError(f"Input not found: {path}")
    unique = list(dict.fromkeys(p.resolve() for p in paths))
    if not unique:
        raise ValueError("No .fit files found in the given inputs")
    if len(unique) > MAX_FILES:
        raise ValueError(f"Too many FIT files ({len(unique)}); pass at most {MAX_FILES}")
    return unique


def read_fit(path: Path) -> FitInput:
    """Validates and decodes one FIT file. Failures are recorded, not raised."""
    from garmin_fit_sdk import Decoder, Stream

    item = FitInput(path=path)
    item.size_bytes = path.stat().st_size
    if path.suffix.lower() != ".fit":
        item.status, item.error = "rejected", "Not a .fit file"
        return item
    if item.size_bytes > MAX_FILE_BYTES:
        item.status, item.error = "rejected", f"Larger than {MAX_FILE_BYTES} bytes"
        return item
    data = path.read_bytes()
    item.sha256 = hashlib.sha256(data).hexdigest()
    if not Decoder(Stream.from_byte_array(bytearray(data))).is_fit():
        item.status, item.error = "rejected", "Not a FIT file"
        return item
    if not Decoder(Stream.from_byte_array(bytearray(data))).check_integrity():
        item.status, item.error = "rejected", "FIT integrity (CRC) check failed"
        return item
    messages, errors = Decoder(Stream.from_byte_array(bytearray(data))).read()
    if errors:
        item.status, item.error = "rejected", "; ".join(str(e) for e in errors)
        return item
    item.status, item.messages = "decoded", messages
    return item


def merge(inputs: List[FitInput]) -> Messages:
    merged: Messages = {}
    seen = set()
    for item in inputs:
        if item.status != "decoded" or item.sha256 in seen:
            continue
        seen.add(item.sha256)
        for key, values in item.messages.items():
            merged.setdefault(key, []).extend(values)
    return merged


def activity_window(messages: Messages) -> Tuple[datetime, datetime]:
    """Uses the recorded activity as the session window when no times are given."""
    sessions = [s for s in messages.get("session_mesgs", []) if session_span(s)]
    if len(sessions) != 1:
        raise ValueError(
            f"Found {len(sessions)} recorded activities; pass --start and --end to choose the session window"
        )
    return session_span(sessions[0])


# --- Sample helpers ---------------------------------------------------------


def session_span(session: Dict[str, Any]) -> Optional[Tuple[datetime, datetime]]:
    start = session.get("start_time")
    elapsed = session.get("total_elapsed_time")
    if not isinstance(start, datetime) or not isinstance(elapsed, (int, float)):
        return None
    return start, start + timedelta(seconds=elapsed)


def sessions_in(messages: Messages, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    found = []
    for session in messages.get("session_mesgs", []):
        span = session_span(session)
        if span and span[0] < end and span[1] > start:
            found.append(session)
    return found


def points(messages: Messages, key: str, time_field: str, value_field: str) -> List[Point]:
    found = []
    for mesg in messages.get(key, []):
        when, value = mesg.get(time_field), mesg.get(value_field)
        if isinstance(when, datetime) and isinstance(value, (int, float)):
            found.append((when, float(value)))
    return found


def interval_points(messages: Messages, key: str, value_field: str) -> List[Point]:
    """Expands array messages where sample i is at timestamp + i * processing_interval."""
    found = []
    for mesg in messages.get(key, []):
        when, step = mesg.get("timestamp"), mesg.get("processing_interval") or 1
        values = mesg.get(value_field)
        if not isinstance(when, datetime) or values is None:
            continue
        for index, value in enumerate(values if isinstance(values, list) else [values]):
            if isinstance(value, (int, float)):
                found.append((when + timedelta(seconds=index * step), float(value)))
    return found


def within(found: List[Point], start: datetime, end: datetime, low: float, high: float) -> List[Point]:
    # Duplicates arise when the same data is exported from Connect and copied from the watch.
    return sorted({(t, v) for t, v in found if start <= t <= end and low <= v <= high})


def stats(found: List[Point], unit: str) -> Dict[str, Any]:
    values = [v for _, v in found]
    return {
        "status": "available",
        "unit": unit,
        "samples": len(values),
        "first": values[0],
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 1),
        "first_time": iso(found[0][0]),
        "last_time": iso(found[-1][0]),
    }


def latest(messages: Messages, key: str, time_field: str, start: datetime, end: datetime) -> Optional[Dict[str, Any]]:
    candidates = [m for m in messages.get(key, []) if isinstance(m.get(time_field), datetime) and start <= m[time_field] <= end]
    return max(candidates, key=lambda m: m[time_field]) if candidates else None


def pick(mesg: Dict[str, Any], fields: List[Tuple[str, str]]) -> Dict[str, Any]:
    return {name: plain(mesg[source]) for source, name in fields if mesg.get(source) is not None}


def plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def not_available(reason: str) -> Dict[str, Any]:
    return {"status": "not_available", "reason": reason}


# --- Metric summaries -------------------------------------------------------


def summarize_heart_rate(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    found = within(points(messages, "record_mesgs", "timestamp", "heart_rate"), start, end, 20, 250)
    return stats(found, "bpm") if found else not_available("No heart-rate records in the session window")


def summarize_stress(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    raw = (
        points(messages, "stress_level_mesgs", "stress_level_time", "stress_level_value")
        + interval_points(messages, "hsa_stress_data_mesgs", "stress_level")
        + points(messages, "record_mesgs", "timestamp", "current_stress")
    )
    in_window = [p for p in raw if start <= p[0] <= end]
    # Garmin uses negative values when stress could not be measured (for example during movement).
    found = within(in_window, start, end, 0, 100)
    averages = [s["avg_stress"] for s in sessions_in(messages, start, end) if s.get("avg_stress") is not None]
    if not found and not averages:
        return not_available(
            "No stress samples in the session window; Garmin often stores stress only in monitoring files"
        )
    result = stats(found, "score 0-100") if found else {"status": "available", "unit": "score 0-100"}
    result["unmeasurable_samples"] = len(in_window) - len(found)
    if averages:
        result["activity_average"] = plain(averages[0])
    result["note"] = "Garmin's estimate from heart-rate variability, not an emotional state"
    return result


def summarize_body_battery(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    found = within(interval_points(messages, "hsa_body_battery_data_mesgs", "level"), start, end, 0, 100)
    if not found:
        return not_available(
            "No Body Battery samples in the files; most watches store it in undocumented monitoring data, "
            "so read it in Garmin Connect instead"
        )
    result = stats(found, "percent")
    result["change"] = found[-1][1] - found[0][1]
    result["note"] = "Garmin's estimated energy reserve"
    return result


def summarize_respiration(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    raw = (
        points(messages, "record_mesgs", "timestamp", "enhanced_respiration_rate")
        + points(messages, "record_mesgs", "timestamp", "respiration_rate")
        + points(messages, "respiration_rate_mesgs", "timestamp", "respiration_rate")
        + interval_points(messages, "hsa_respiration_data_mesgs", "respiration_rate")
    )
    # Negative values are Garmin's "could not measure" markers.
    found = within(raw, start, end, 1, 60)
    if found:
        return stats(found, "breaths/min")
    for session in sessions_in(messages, start, end):
        summary = pick(session, [
            ("enhanced_avg_respiration_rate", "mean"),
            ("enhanced_min_respiration_rate", "min"),
            ("enhanced_max_respiration_rate", "max"),
            ("avg_respiration_rate", "mean"),
            ("min_respiration_rate", "min"),
            ("max_respiration_rate", "max"),
        ])
        if summary:
            return {"status": "available", "unit": "breaths/min", "source": "activity summary", **summary}
    return not_available("No respiration data in the session window")


ACTIVITY_FIELDS = [
    ("sport", "sport"),
    ("sub_sport", "sub_sport"),
    ("start_time", "start_time"),
    ("total_elapsed_time", "elapsed_seconds"),
    ("total_timer_time", "timer_seconds"),
    ("total_calories", "calories_kcal"),
    ("total_distance", "distance_m"),
    ("avg_heart_rate", "avg_heart_rate_bpm"),
    ("min_heart_rate", "min_heart_rate_bpm"),
    ("max_heart_rate", "max_heart_rate_bpm"),
    ("total_ascent", "ascent_m"),
    ("total_descent", "descent_m"),
    ("time_in_hr_zone", "time_in_hr_zone_seconds"),
    ("avg_spo2", "avg_spo2_percent"),
]


def summarize_activity(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    sessions = [pick(s, ACTIVITY_FIELDS) for s in sessions_in(messages, start, end)]
    result: Dict[str, Any] = {"recordings": sessions, "heart_rate": summarize_heart_rate(messages, start, end)}
    if not sessions:
        result["reason"] = "No activity recording overlaps the session window"
    return result


def summarize_fitness(messages: Messages, start: datetime, end: datetime) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    vo2 = latest(messages, "max_met_data_mesgs", "update_time", datetime.min.replace(tzinfo=timezone.utc), end)
    result["vo2_max"] = (
        {"status": "available", "unit": "mL/kg/min", **pick(vo2, [("vo2_max", "value"), ("update_time", "updated"), ("sport", "sport")])}
        if vo2 and vo2.get("vo2_max") is not None
        else not_available("No VO2 max estimate in the files (often in the watch's metrics files)")
    )
    resting = latest(messages, "monitoring_hr_data_mesgs", "timestamp", end - timedelta(days=7), end)
    result["resting_heart_rate"] = (
        {"status": "available", "unit": "bpm", **pick(resting, [
            ("resting_heart_rate", "seven_day_average"),
            ("current_day_resting_heart_rate", "current_day"),
            ("timestamp", "time"),
        ])}
        if resting
        else not_available("No resting heart rate in the files from the past 7 days")
    )
    effects = [
        pick(s, [
            ("total_training_effect", "aerobic_training_effect"),
            ("total_anaerobic_training_effect", "anaerobic_training_effect"),
            ("training_load_peak", "training_load"),
        ])
        for s in sessions_in(messages, start, end)
    ]
    effects = [e for e in effects if e]
    result["training_effect"] = (
        {"status": "available", **effects[0]} if effects else not_available("No training effect in the activity recording")
    )
    return result


def summarize_sleep(inputs: List[FitInput], night_start: datetime, night_end: datetime) -> Dict[str, Any]:
    found: List[Tuple[datetime, str]] = []
    assessment: Dict[str, Any] = {}
    for item in inputs:
        if item.status != "decoded":
            continue
        levels = [
            (m["timestamp"], m["sleep_level"])
            for m in item.messages.get("sleep_level_mesgs", [])
            if isinstance(m.get("timestamp"), datetime) and night_start <= m["timestamp"] <= night_end
            and m.get("sleep_level") in SLEEP_LEVELS
        ]
        found.extend(levels)
        # The assessment message has no timestamp, so only trust it from a file with sleep stages in this night.
        if levels and not assessment and item.messages.get("sleep_assessment_mesgs"):
            assessment = pick(item.messages["sleep_assessment_mesgs"][0], [
                ("overall_sleep_score", "overall_score"),
                ("sleep_quality_score", "quality_score"),
                ("sleep_duration_score", "duration_score"),
                ("deep_sleep_score", "deep_score"),
                ("light_sleep_score", "light_score"),
                ("rem_sleep_score", "rem_score"),
                ("sleep_recovery_score", "recovery_score"),
                ("awakenings_count", "awakenings"),
                ("average_stress_during_sleep", "average_stress_during_sleep"),
            ])
    found = sorted(set(found))
    if len(found) < 2:
        return not_available("No sleep stages in the night before the session (often in the watch's sleep files)")
    # Each stage lasts until the next transition; the final transition marks the end.
    minutes = {level: 0.0 for level in SLEEP_LEVELS}
    for (when, level), (after, _) in zip(found, found[1:]):
        minutes[level] += (after - when).total_seconds() / 60
    result: Dict[str, Any] = {
        "status": "available",
        "start": iso(found[0][0]),
        "end": iso(found[-1][0]),
        "minutes": {k: round(v, 1) for k, v in minutes.items()},
        "total_sleep_minutes": round(minutes["light"] + minutes["deep"] + minutes["rem"], 1),
    }
    if assessment:
        result["assessment"] = assessment
    return result


def summarize_skin_temperature(messages: Messages, night_start: datetime, night_end: datetime) -> Dict[str, Any]:
    night = latest(messages, "skin_temp_overnight_mesgs", "timestamp", night_start, night_end)
    if not night:
        return not_available("No overnight skin temperature in the night before the session")
    return {
        "status": "available",
        "unit": "degrees C",
        **pick(night, [
            ("timestamp", "time"),
            ("nightly_value", "nightly_value"),
            ("average_deviation", "deviation_from_baseline"),
            ("average_7_day_deviation", "seven_day_deviation"),
        ]),
        "note": "Overnight change relative to the wearer's own baseline",
    }


def summarize_hrv_status(messages: Messages, night_start: datetime, night_end: datetime) -> Dict[str, Any]:
    night = latest(messages, "hrv_status_summary_mesgs", "timestamp", night_start, night_end)
    if not night:
        return not_available("No overnight HRV status in the night before the session")
    return {
        "status": "available",
        "unit": "ms",
        **pick(night, [
            ("timestamp", "time"),
            ("last_night_average", "last_night_average"),
            ("weekly_average", "weekly_average"),
            ("status", "garmin_status"),
        ]),
    }


def build_summary(
    inputs: List[FitInput],
    start: datetime,
    end: datetime,
    night_lookback_hours: float = DEFAULT_NIGHT_LOOKBACK_HOURS,
    session_id: str = "",
) -> Dict[str, Any]:
    if end <= start:
        raise ValueError("Session end must be after its start")
    if end - start > timedelta(hours=MAX_SESSION_HOURS):
        raise ValueError(f"Session window is longer than {MAX_SESSION_HOURS} hours")
    messages = merge(inputs)
    night_start = start - timedelta(hours=night_lookback_hours)
    session = {
        "stress": summarize_stress(messages, start, end),
        "body_battery": summarize_body_battery(messages, start, end),
        "respiration": summarize_respiration(messages, start, end),
        "activity": summarize_activity(messages, start, end),
        "fitness": summarize_fitness(messages, start, end),
    }
    night = {
        "sleep": summarize_sleep(inputs, night_start, start),
        "skin_temperature": summarize_skin_temperature(messages, night_start, start),
        "hrv_status": summarize_hrv_status(messages, night_start, start),
    }
    return {
        "summary_version": SUMMARY_VERSION,
        "session_id": session_id or None,
        "session_window": {"start": iso(start), "end": iso(end), "minutes": round((end - start).total_seconds() / 60, 1)},
        "night_window": {"start": iso(night_start), "end": iso(start)},
        "session": session,
        "previous_night": night,
        "limits": LIMITS,
    }


# --- Run output -------------------------------------------------------------


def write_run(output_dir: Path, summary: Optional[Dict[str, Any]], manifest: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if summary is not None:
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Garmin end-of-session summary from local FIT files")
    parser.add_argument("inputs", nargs="+", help="FIT files or folders containing them")
    parser.add_argument("--start", help="Session start, ISO 8601 (default: the recorded activity's start)")
    parser.add_argument("--end", help="Session end, ISO 8601 (default: the recorded activity's end)")
    parser.add_argument("--session-id", default="", help="Inner Landscape session ID to label the summary")
    parser.add_argument("--night-hours", type=float, default=DEFAULT_NIGHT_LOOKBACK_HOURS,
                        help="Hours before the session searched for sleep data (default: 24)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Run folder (default: runs/garmin/<run_id>)")
    args = parser.parse_args(argv)

    run_id = f"summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output_dir = args.output_dir or Path(__file__).resolve().parents[1] / "runs" / "garmin" / run_id
    manifest: Dict[str, Any] = {
        "manifest_version": "1.0",
        "summary_version": SUMMARY_VERSION,
        "fit_sdk_version": FIT_SDK_VERSION,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": [Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])],
        "parameters": {
            "start": args.start,
            "end": args.end,
            "session_id": args.session_id or None,
            "night_hours": args.night_hours,
        },
        "inputs": [],
        "status": "failed",
        "outputs": {"manifest": str(output_dir / "manifest.json")},
    }

    if not 0 <= args.night_hours <= 48:
        print("--night-hours must be between 0 and 48", file=sys.stderr)
        return 2
    if bool(args.start) != bool(args.end):
        print("Pass both --start and --end, or neither to use the recorded activity", file=sys.stderr)
        return 2
    try:
        start, end = (parse_time(args.start), parse_time(args.end)) if args.start else (None, None)
        paths = collect_paths(args.inputs)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    try:
        import garmin_fit_sdk  # noqa: F401
    except ImportError:
        print(f"Missing dependency: install garmin-fit-sdk=={FIT_SDK_VERSION}", file=sys.stderr)
        return 2

    inputs = [read_fit(path) for path in paths]
    manifest["inputs"] = [item.describe() for item in inputs]
    for item in inputs:
        print(f"  {item.status:8} {item.path.name}" + (f" ({item.error})" if item.error else ""))
    if not any(item.status == "decoded" for item in inputs):
        manifest["error"] = "No FIT file could be decoded"
        write_run(output_dir, None, manifest)
        print(f"Error: {manifest['error']}. Manifest written to {output_dir}", file=sys.stderr)
        return 1

    try:
        if start is None:
            start, end = activity_window(merge(inputs))
        summary = build_summary(inputs, start, end, args.night_hours, args.session_id)
    except ValueError as error:
        manifest["error"] = str(error)
        write_run(output_dir, None, manifest)
        print(f"Error: {error}. Manifest written to {output_dir}", file=sys.stderr)
        return 1

    manifest["status"] = "completed"
    manifest["resolved_window"] = summary["session_window"]
    manifest["outputs"]["summary"] = str(output_dir / "summary.json")
    write_run(output_dir, summary, manifest)

    print(f"\nSession {summary['session_window']['start']} to {summary['session_window']['end']}")
    sections = {**summary["session"], **summary["previous_night"]}
    for name, value in sections.items():
        state = value.get("status") or ("available" if value.get("recordings") else "not_available")
        if name == "fitness":
            state = ", ".join(f"{k}: {v['status']}" for k, v in value.items())
        print(f"  {name:17} {state}")
    print(f"\n[Summary saved] Output written to {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
