"""Verify static bake color retention and world-coordinate centering."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import trimesh

SCRIPT = Path(__file__).resolve().parents[1] / "experiments/refine_portraits_twice.py"
spec = importlib.util.spec_from_file_location("portrait_refinement", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def test_world_center_and_vertex_colors_survive_both_formats(self):
        logits = torch.full((1, 16, 16, 16), -10.0)
        logits[:, 4:12, 4:12, 4:12] = 10.0
        red = torch.full((3, 16, 16, 16), -10.0)
        red[0] = 10.0
        blue = torch.full_like(red, -10.0)
        blue[2] = 10.0
        model = SimpleNamespace(
            log_densities=logits,
            log_colors1=red,
            log_colors2=blue,
            inner_temperature=1.0,
            density_bias=0.0,
            outer_scale=1.0,
            density_scale=1.0,
            spatial_mask=torch.ones_like(logits),
            _voxel_size=0.1,
        )
        cameras = [
            SimpleNamespace(get_camera_center=lambda: torch.tensor([[-5.0, 0.0, 5.0]])),
            SimpleNamespace(get_camera_center=lambda: torch.tensor([[5.0, 0.0, 5.0]])),
        ]
        with tempfile.TemporaryDirectory() as directory:
            module.mesh_export(model, cameras, Path(directory))
            for suffix in ("obj", "ply"):
                mesh = trimesh.load(
                    Path(directory) / f"sculpture.{suffix}", force="mesh", process=False
                )
                self.assertTrue(mesh.is_watertight)
                np.testing.assert_allclose(mesh.bounds.mean(axis=0), 0, atol=0.02)
                self.assertEqual(mesh.visual.kind, "vertex")
                colors = mesh.visual.vertex_colors
                self.assertTrue((colors[:, 0] > 200).any())
                self.assertTrue((colors[:, 2] > 200).any())
