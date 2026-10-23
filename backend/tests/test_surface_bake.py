import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh
from borrowed_eyes.mesh_preview import render_mesh
from borrowed_eyes.surface_bake import build_surface, cameras
from PIL import Image, ImageDraw


class SurfaceBakeTests(unittest.TestCase):
    def test_two_views_retain_distinct_colors_and_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for index, color in enumerate(((255, 0, 0, 255), (0, 0, 255, 255))):
                image = Image.new("RGBA", (64, 64))
                ImageDraw.Draw(image).rectangle((16, 10, 47, 53), fill=color)
                path = root / f"input{index}.png"
                image.save(path)
                sources.append(path)
            before = [p.read_bytes() for p in sources]
            output = root / "mesh"
            build_surface(*sources, output, resolution=40)
            for index, camera in enumerate(cameras()):
                render = render_mesh(output / "sculpture.ply", camera, 64) / 255
                foreground = render.sum(axis=2) > 0.1
                target = np.zeros((64, 64), dtype=bool)
                target[10:54, 16:48] = True
                iou = (foreground & target).sum() / (foreground | target).sum()
                self.assertGreater(iou, 0.85)
                self.assertGreater(render[:, :, index * 2][target & foreground].mean(), 0.85)
            self.assertEqual(before, [p.read_bytes() for p in sources])
            for extension in ("obj", "ply"):
                mesh = trimesh.load(output / f"sculpture.{extension}", force="mesh", process=False)
                self.assertEqual(mesh.visual.kind, "vertex")
                geometry = trimesh.Trimesh(mesh.vertices, mesh.faces, process=False)
                geometry.merge_vertices()
                self.assertTrue(geometry.is_watertight)
            with self.assertRaises(FileExistsError):
                build_surface(*sources, output, resolution=40)

    def test_invalid_resolution_rejected_before_output(self):
        with self.assertRaises(ValueError):
            build_surface(Path("missing"), Path("missing"), Path("unused"), resolution=1)
