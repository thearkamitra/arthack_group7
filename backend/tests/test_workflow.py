import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from borrowed_eyes.images import apply_mask, remove_background
from borrowed_eyes.workflow import TrainingConfig, export_mesh, pipeline, train
from PIL import Image


class WorkflowTests(unittest.TestCase):
    def test_mask_preserves_rgb_and_existing_alpha(self):
        source = Image.new("RGBA", (2, 1), (12, 34, 56, 128))
        mask = Image.new("L", (2, 1), 255)
        mask.putpixel((0, 0), 0)
        output = apply_mask(source, mask)
        self.assertEqual(list(output.convert("RGB").getdata()), [(12, 34, 56)] * 2)
        self.assertEqual(list(output.getchannel("A").getdata()), [0, 128])
        self.assertEqual(source.getpixel((0, 0)), (12, 34, 56, 128))

    def test_invalid_grid_rejected(self):
        with self.assertRaises(ValueError):
            TrainingConfig(volume_size=32).validate()

    def test_output_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.png"
            Image.new("RGB", (2, 2)).save(path)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                remove_background(path, path, Path(directory) / "cache")
            self.assertEqual(original, path.read_bytes())

    def make_rgba(self, path):
        image = Image.new("RGBA", (2, 2), (100, 120, 150, 255))
        image.putpixel((0, 0), (100, 120, 150, 0))
        image.save(path)

    def test_failed_train_marks_manifest_and_preserves_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.png", root / "two.png"
            self.make_rgba(one)
            self.make_rgba(two)
            original = one.read_bytes()
            with patch("borrowed_eyes.workflow.train", side_effect=RuntimeError("training failed")):
                with self.assertRaises(RuntimeError):
                    pipeline(one, two, root / "jobs", TrainingConfig(), prepared=True)
            manifest = json.loads(next((root / "jobs").glob("*/manifest.json")).read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("training failed", manifest["error"])
            self.assertEqual(original, one.read_bytes())

    def test_success_without_checkpoint_is_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.png", root / "two.png"
            self.make_rgba(one)
            self.make_rgba(two)
            with patch("borrowed_eyes.workflow.execute"):
                with self.assertRaisesRegex(RuntimeError, "checkpoint"):
                    train(one, two, root / "job", TrainingConfig())

    def test_export_reloads_real_geometry(self):
        import torch
        import trimesh

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "model.pt"
            torch.save({"voxel_size": 0.0234375}, checkpoint)

            def export_fixture(command, log):
                self.assertIn("0.0234375", command)
                log.write_text("Test export\n")
                mesh = trimesh.creation.box()
                for extension in ("obj", "ply"):
                    mesh.export(root / "export" / f"sculpture.{extension}")

            with patch("borrowed_eyes.workflow.execute", side_effect=export_fixture):
                results = export_mesh(checkpoint, root / "export")
            self.assertEqual(results["obj"]["triangles"], 12)
            self.assertTrue(results["ply"]["watertight"])

    def test_process_failure_propagates(self):
        from borrowed_eyes.workflow import execute

        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "run.log"
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["failed"])):
                with self.assertRaises(subprocess.CalledProcessError):
                    execute(["failed"], log)
            self.assertEqual(json.loads(log.with_suffix(".command.json").read_text()), ["failed"])

    def test_invalid_camera_rejected(self):
        with self.assertRaises(ValueError):
            TrainingConfig(azim1=float("nan")).validate()


if __name__ == "__main__":
    unittest.main()
