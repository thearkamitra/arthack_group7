"""Static two-view visual-hull construction and projection color bake.
This reconstructs a fixed mesh from masks; it does not export trained volume colors.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
import trimesh
from PIL import Image
from pytorch3d.renderer import OrthographicCameras, look_at_view_transform
from scipy.ndimage import map_coordinates
from skimage.measure import marching_cubes


def cameras():
    result = []
    for azimuth in (-45, 45):
        rotation, translation = look_at_view_transform(dist=3.0, elev=0, azim=azimuth)
        result.append(
            OrthographicCameras(R=rotation, T=translation, focal_length=((2 / 3, 2 / 3),))
        )
    return result


def project(points: np.ndarray, camera, size: int) -> np.ndarray:
    tensor = torch.tensor(points, dtype=torch.float32)[None]
    result = camera.transform_points_screen(tensor, image_size=((size, size),))[0].numpy()
    result[:, 2] = camera.get_world_to_view_transform().transform_points(tensor)[0, :, 2].numpy()
    return result


def sample_image(image: np.ndarray, xy: np.ndarray) -> np.ndarray:
    return np.stack(
        [
            map_coordinates(
                image[:, :, channel],
                [xy[:, 1] - 0.5, xy[:, 0] - 0.5],
                order=1,
                mode="constant",
                cval=0,
            )
            for channel in range(image.shape[2])
        ],
        axis=1,
    )


def _build_surface(one: Path, two: Path, output: Path, resolution: int = 128) -> Path:
    if resolution < 16 or resolution > 256:
        raise ValueError("Resolution must be between 16 and 256")
    images = []
    for path in (one, two):
        with Image.open(path) as image:
            if image.mode != "RGBA" or image.width != image.height:
                raise ValueError("Inputs must be square normalized RGBA images")
            images.append(np.array(image) / 255.0)
    if images[0].shape != images[1].shape:
        raise ValueError("Input canvas dimensions must match")
    for image in images:
        low, high = image[:, :, 3].min(), image[:, :, 3].max()
        if low >= 0.5 or high <= 0.5:
            raise ValueError("Each input needs foreground and transparency")
    size = images[0].shape[0]
    output.mkdir(parents=True, exist_ok=False)
    cam = cameras()
    axis = np.linspace(-1.5, 1.5, resolution, dtype=np.float32)
    # Keep array order xyz explicit; marching cubes indices use the same order.
    grid = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    points = grid.reshape(-1, 3)
    occupancy = np.ones(len(points), dtype=bool)
    for camera, image in zip(cam, images):
        xy = project(points, camera, size)
        occupancy &= sample_image(image, xy)[:, 3] > 0.5
    occupancy = occupancy.reshape((resolution,) * 3)
    # Empty boundary closes the hull even if a silhouette touches the grid edge.
    occupancy[[0, -1], :, :] = False
    occupancy[:, [0, -1], :] = False
    occupancy[:, :, [0, -1]] = False
    if not occupancy.any():
        raise ValueError("Silhouette intersection is empty")
    vertices, faces, _, _ = marching_cubes(occupancy.astype(np.float32), level=0.5)
    vertices = vertices * (3 / (resolution - 1)) - 1.5
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.fix_normals()
    # All rays in an orthographic camera share one direction.
    centers = np.stack([camera.get_camera_center()[0].numpy() for camera in cam])
    view_dirs = centers / np.linalg.norm(centers, axis=1, keepdims=True)
    scores = mesh.face_normals @ view_dirs.T
    labels = np.argmax(scores, axis=1)
    # Duplicate only at color seams, not every triangle; retain a weldable surface.
    unique_keys, inverse = np.unique(
        np.column_stack([faces.reshape(-1), np.repeat(labels, 3)]), axis=0, return_inverse=True
    )
    split_vertices = vertices[unique_keys[:, 0]]
    split_faces = inverse.reshape(-1, 3)
    rgb = np.zeros((len(split_vertices), 3))
    for index, (camera, image) in enumerate(zip(cam, images)):
        selected = unique_keys[:, 1] == index
        xy = project(split_vertices[selected], camera, size)
        rgb[selected] = sample_image(image, xy)[:, :3]
    colored = trimesh.Trimesh(split_vertices, split_faces, process=False)
    colored.visual.vertex_colors = np.column_stack(
        [(rgb.clip(0, 1) * 255).astype("uint8"), np.full(len(rgb), 255, dtype="uint8")]
    )
    report = {}
    for suffix in ("ply", "obj"):
        path = output / f"sculpture.{suffix}"
        colored.export(path)
        loaded = trimesh.load(path, force="mesh", process=False)
        if not np.isfinite(loaded.vertices).all() or loaded.visual.kind != "vertex":
            raise RuntimeError("Geometry or vertex colors did not survive export")
        welded = trimesh.Trimesh(loaded.vertices, loaded.faces, process=False)
        welded.merge_vertices()
        report[suffix] = {
            "vertices": len(loaded.vertices),
            "triangles": len(loaded.faces),
            "vertex_colors": True,
            "indexed_watertight": bool(loaded.is_watertight),
            "position_welded_watertight": bool(welded.is_watertight),
        }
    root = Path(__file__).resolve().parents[2]
    manifest = {
        "status": "complete",
        "command": sys.argv,
        "algorithm_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment_sha256": hashlib.sha256(
            (root / "backend/requirements-macos.lock.txt").read_bytes()
        ).hexdigest(),
        "submodule_commit": subprocess.check_output(
            ["git", "-C", str(root / "external/Auto-MIA"), "rev-parse", "HEAD"], text=True
        ).strip(),
        "method": "two-view silhouette intersection with fixed projection vertex-color bake",
        "uses_optimized_checkpoint_geometry": False,
        "training_iterations": 0,
        "resolution": resolution,
        "world_bounds": [-1.5, 1.5],
        "azimuths": [-45, 45],
        "elevations": [0, 0],
        "source_images": [
            {"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in (one, two)
        ],
        "validation": report,
        "limitations": "Only two views constrained; color seams split vertex indices. Intermediate and stereo views unvalidated.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return output / "sculpture.ply"


def build_surface(one: Path, two: Path, output: Path, resolution: int = 128) -> Path:
    """Build once and leave explicit failure metadata for newly created outputs."""
    existed = output.exists()
    try:
        return _build_surface(one, two, output, resolution)
    except Exception as exc:
        if not existed and output.is_dir():
            (output / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "method": "two-view silhouette intersection with projection colors",
                        "inputs": [str(one), str(two)],
                        "resolution": resolution,
                    },
                    indent=2,
                )
            )
        raise
