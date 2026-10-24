import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from garmin_session_summary import (  # noqa: E402
    FitInput,
    activity_window,
    build_summary,
    collect_paths,
    main,
    parse_time,
)

try:
    from garmin_fit_sdk import Encoder, Profile
except ImportError:
    Encoder = None

START = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
END = START + timedelta(minutes=20)


def at(minutes):
    return START + timedelta(minutes=minutes)


def activity():
    return {
        "session_mesgs": [{
            "start_time": START,
            "total_elapsed_time": 1200.0,
            "total_calories": 40,
            "avg_heart_rate": 72,
            "max_heart_rate": 90,
            "sport": "training",
            "total_training_effect": 1.2,
        }],
        "record_mesgs": [
            {"timestamp": at(0), "heart_rate": 70, "enhanced_respiration_rate": 14.0},
            {"timestamp": at(10), "heart_rate": 80, "enhanced_respiration_rate": 16.0},
            {"timestamp": at(30), "heart_rate": 150, "enhanced_respiration_rate": 30.0},
        ],
    }


def monitoring():
    return {
        "stress_level_mesgs": [
            {"stress_level_time": at(-5), "stress_level_value": 90},
            {"stress_level_time": at(2), "stress_level_value": 20},
            {"stress_level_time": at(5), "stress_level_value": -1},
            {"stress_level_time": at(8), "stress_level_value": 40},
        ],
        "hsa_body_battery_data_mesgs": [
            {"timestamp": at(0), "processing_interval": 300, "level": [60, 59, 58, 57, 56]},
        ],
    }


def sleep():
    night = START - timedelta(hours=10)
    return {
        "sleep_level_mesgs": [
            {"timestamp": night, "sleep_level": "light"},
            {"timestamp": night + timedelta(hours=1), "sleep_level": "deep"},
            {"timestamp": night + timedelta(hours=2), "sleep_level": "rem"},
            {"timestamp": night + timedelta(hours=2, minutes=30), "sleep_level": "awake"},
        ],
        "sleep_assessment_mesgs": [{"overall_sleep_score": 78, "awakenings_count": 2}],
        "skin_temp_overnight_mesgs": [
            {"timestamp": START - timedelta(hours=3), "average_deviation": -0.3, "nightly_value": 33.1},
        ],
    }


def decoded(messages, name):
    return FitInput(path=Path(name), sha256=name, status="decoded", messages=messages)


class SessionSummaryTests(unittest.TestCase):
    def summary(self, *inputs):
        return build_summary(list(inputs), START, END)

    def test_session_window_limits_samples(self):
        result = self.summary(decoded(activity(), "a"))
        hr = result["session"]["activity"]["heart_rate"]
        self.assertEqual((hr["samples"], hr["min"], hr["max"]), (2, 70, 80))
        respiration = result["session"]["respiration"]
        self.assertEqual((respiration["samples"], respiration["mean"]), (2, 15.0))
        self.assertEqual(result["session"]["activity"]["recordings"][0]["calories_kcal"], 40)
        self.assertEqual(result["session"]["fitness"]["training_effect"]["aerobic_training_effect"], 1.2)

    def test_stress_excludes_unmeasurable_and_out_of_window(self):
        stress = self.summary(decoded(monitoring(), "m"))["session"]["stress"]
        self.assertEqual((stress["samples"], stress["mean"], stress["unmeasurable_samples"]), (2, 30.0, 1))
        self.assertIn("not an emotional state", stress["note"])

    def test_body_battery_expands_interval_arrays(self):
        battery = self.summary(decoded(monitoring(), "m"))["session"]["body_battery"]
        # 5 samples at 5-minute steps; the one at 20 minutes is the window end and included.
        self.assertEqual((battery["samples"], battery["first"], battery["last"], battery["change"]), (5, 60, 56, -4))

    def test_previous_night_sleep_and_skin_temperature(self):
        night = self.summary(decoded(sleep(), "s"))["previous_night"]
        self.assertEqual(night["sleep"]["minutes"]["light"], 60)
        self.assertEqual(night["sleep"]["total_sleep_minutes"], 150)
        self.assertEqual(night["sleep"]["assessment"]["overall_score"], 78)
        self.assertEqual(night["skin_temperature"]["deviation_from_baseline"], -0.3)

    def test_missing_metrics_are_not_available(self):
        result = self.summary(decoded(activity(), "a"))
        for value in (
            result["session"]["stress"],
            result["session"]["body_battery"],
            result["previous_night"]["sleep"],
            result["previous_night"]["skin_temperature"],
            result["session"]["fitness"]["vo2_max"],
        ):
            self.assertEqual(value["status"], "not_available")
            self.assertTrue(value["reason"])

    def test_duplicate_files_and_rejected_inputs_are_ignored(self):
        rejected = FitInput(path=Path("bad.fit"), status="rejected", messages=monitoring())
        result = self.summary(decoded(activity(), "same"), decoded(activity(), "same"), rejected)
        self.assertEqual(result["session"]["activity"]["heart_rate"]["samples"], 2)
        self.assertEqual(len(result["session"]["activity"]["recordings"]), 1)
        self.assertEqual(result["session"]["stress"]["status"], "not_available")

    def test_activity_defines_default_window(self):
        self.assertEqual(activity_window(activity()), (START, END))
        two = activity()
        two["session_mesgs"].append(dict(two["session_mesgs"][0]))
        with self.assertRaises(ValueError):
            activity_window(two)

    def test_rejects_invalid_windows(self):
        with self.assertRaises(ValueError):
            build_summary([], END, START)
        with self.assertRaises(ValueError):
            build_summary([], START, START + timedelta(hours=13))

    def test_parse_time_requires_valid_iso(self):
        self.assertEqual(parse_time("2026-10-24T12:00:00+02:00"), START)
        self.assertEqual(parse_time("2026-10-24T10:00:00Z"), START)
        with self.assertRaises(ValueError):
            parse_time("yesterday")

    def test_collect_paths_requires_fit_files(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                collect_paths([folder])
            with self.assertRaises(ValueError):
                collect_paths([str(Path(folder) / "missing.fit")])


@unittest.skipIf(Encoder is None, "garmin-fit-sdk is not installed")
class FitFileTests(unittest.TestCase):
    def test_end_to_end_with_encoded_fit_file(self):
        mesg_num = Profile["mesg_num"]
        encoder = Encoder()
        encoder.write_mesg({"mesg_num": mesg_num["FILE_ID"], "type": "activity", "manufacturer": "garmin", "time_created": START})
        for minute, bpm in ((0, 70), (10, 80)):
            encoder.write_mesg({"mesg_num": mesg_num["RECORD"], "timestamp": at(minute), "heart_rate": bpm, "enhanced_respiration_rate": 14.5})
        encoder.write_mesg({"mesg_num": mesg_num["STRESS_LEVEL"], "stress_level_time": at(5), "stress_level_value": 25})
        encoder.write_mesg({"mesg_num": mesg_num["SESSION"], "timestamp": END, "start_time": START, "total_elapsed_time": 1200, "total_calories": 40})
        with tempfile.TemporaryDirectory() as folder:
            fit = Path(folder) / "activity.fit"
            fit.write_bytes(encoder.close())
            (Path(folder) / "broken.fit").write_bytes(b"not a fit file")
            output = Path(folder) / "run"
            self.assertEqual(main([folder, "--output-dir", str(output), "--session-id", "session-test"]), 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["session_id"], "session-test")
        self.assertEqual(summary["session_window"]["minutes"], 20)
        self.assertEqual(summary["session"]["stress"]["mean"], 25)
        self.assertEqual(summary["session"]["respiration"]["mean"], 14.5)
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(sorted(i["status"] for i in manifest["inputs"]), ["decoded", "rejected"])

    def test_synthetic_demo_files_fill_every_metric(self):
        import make_demo_garmin_fit as demo

        with tempfile.TemporaryDirectory() as folder:
            for name, build in (("a", demo.activity), ("m", demo.monitoring), ("s", demo.sleep), ("x", demo.metrics)):
                (Path(folder) / f"{name}.fit").write_bytes(build())
            output = Path(folder) / "run"
            self.assertEqual(main([folder, "--output-dir", str(output)]), 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        session, night = summary["session"], summary["previous_night"]
        for value in (session["stress"], session["body_battery"], session["respiration"],
                      session["activity"]["heart_rate"], *session["fitness"].values(), *night.values()):
            self.assertEqual(value["status"], "available")
        self.assertEqual(summary["session_window"]["minutes"], 4)

    def test_no_decodable_file_fails_with_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "broken.fit").write_bytes(b"not a fit file")
            output = Path(folder) / "run"
            self.assertEqual(main([folder, "--output-dir", str(output)]), 1)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse((output / "summary.json").exists())
        self.assertEqual(manifest["status"], "failed")


if __name__ == "__main__":
    unittest.main()
