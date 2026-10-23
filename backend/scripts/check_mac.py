"""Small backend checks; does not run training or change the submodule."""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import mlx.core as mx
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "external" / "Auto-MIA"))
from volume_illusion.model import VolumeModel, create_dual_view_cameras
from volume_illusion.renderer import create_volume_renderer

results = {"torch": torch.__version__, "mps_available": torch.backends.mps.is_available()}
try:
    with mx.stream(mx.gpu):
        x = mx.ones((32, 32))
        y = mx.sum(x @ x)
        mx.eval(y)
        results["mlx_gpu"] = float(y.item()) == 32768.0
except Exception as exc:
    results["mlx_gpu"] = f"{type(exc).__name__}: {exc}"

for device in ("cpu", "mps"):
    try:
        renderer = create_volume_renderer(16, n_pts_per_ray=16, device=device, orthographic=True)
        model = VolumeModel(renderer, volume_size=[16] * 3, voxel_size=3.0 / 16).to(device)
        cameras = create_dual_view_cameras(device=device, orthographic=True)
        loss = sum(model(camera).square().mean() for camera in cameras)
        loss.backward()
        assert torch.isfinite(loss).item()
        assert model.log_densities.grad is not None
        assert torch.isfinite(model.log_densities.grad).all().item()
        results[device] = "two-view volume render and density backward passed (16 cubed)"
    except Exception as exc:
        results[device] = f"{type(exc).__name__}: {exc}"

print(json.dumps(results, indent=2))
