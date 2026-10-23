from pathlib import Path

import numpy as np
import torch
import trimesh
from numba import njit


@njit
def raster(points, faces, colors, size):
    image = np.zeros((size, size, 3))
    depth = np.full((size, size), 1e10)
    for f in faces:
        a, b, c = points[f[0]], points[f[1]], points[f[2]]
        denom = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denom) < 1e-10:
            continue
        x0 = max(0, int(np.floor(min(a[0], b[0], c[0]))))
        x1 = min(size - 1, int(np.ceil(max(a[0], b[0], c[0]))))
        y0 = max(0, int(np.floor(min(a[1], b[1], c[1]))))
        y1 = min(size - 1, int(np.ceil(max(a[1], b[1], c[1]))))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                u = ((b[1] - c[1]) * (x + 0.5 - c[0]) + (c[0] - b[0]) * (y + 0.5 - c[1])) / denom
                v = ((c[1] - a[1]) * (x + 0.5 - c[0]) + (a[0] - c[0]) * (y + 0.5 - c[1])) / denom
                w = 1 - u - v
                if min(u, v, w) < -1e-8:
                    continue
                z = u * a[2] + v * b[2] + w * c[2]
                if z <= 0 or z >= depth[y, x]:
                    continue
                depth[y, x] = z
                image[y, x] = u * colors[f[0]] + v * colors[f[1]] + w * colors[f[2]]
    return image


def render_mesh(path: Path, camera, size: int = 128) -> np.ndarray:
    mesh = trimesh.load(path, force="mesh", process=False)
    points = torch.tensor(mesh.vertices, dtype=torch.float32)[None]
    screen = camera.transform_points_screen(points, image_size=((size, size),))[0].numpy()
    screen[:, 2] = camera.get_world_to_view_transform().transform_points(points)[0, :, 2].numpy()
    rgb = raster(screen, np.asarray(mesh.faces), mesh.visual.vertex_colors[:, :3] / 255, size)
    return (rgb.clip(0, 1) * 255).astype("uint8")
