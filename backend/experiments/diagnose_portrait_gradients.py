import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "external/Auto-MIA"))
import numpy as np
import torch
from PIL import Image
from volume_illusion.model import VolumeModel, create_dual_view_cameras
from volume_illusion.renderer import create_volume_renderer

job = root / "runs/normalized-trials/20261023T220145Z-40fb6c62"
checkpoint = next(job.glob("*/models/*.pt"))
state = torch.load(checkpoint, map_location="cpu", weights_only=True)["state_dict"]
diagnostics = root / "work/portrait-diagnostics"
diagnostics.mkdir(parents=True, exist_ok=True)
results = []
reference = {}
for device in ("cpu", "mps"):
    model = VolumeModel(
        create_volume_renderer(32, n_pts_per_ray=64, device=device, orthographic=True),
        volume_size=[128] * 3,
        voxel_size=3 / 128,
    ).to(device)
    model.load_state_dict(state)
    model.inner_temperature = 2.25
    model.outer_scale = 0.8
    model.density_bias = 0.5
    model.log_densities.requires_grad_(False)
    cams = create_dual_view_cameras(device=device, azim1=-45, azim2=45, orthographic=True)
    for i, cam in enumerate(cams, 1):
        model.zero_grad(set_to_none=True)
        im = Image.open(job / f"normalized/input_{i}_rgba.png").resize((32, 32))
        ar = np.array(im) / 255.0
        target = torch.tensor(ar[:, :, :3], dtype=torch.float32, device=device)
        mask = torch.tensor(ar[:, :, 3] > 0.5, device=device)
        out = model(cam)[0, :, :, :3]
        loss = (out - target).abs()[mask].mean()
        loss.backward()
        rec = {
            "device": device,
            "view": i,
            "center": cam.get_camera_center().detach().cpu().tolist(),
            "loss": loss.item(),
            "pred_mean": out[mask].mean().item(),
        }
        for name in ("log_colors1", "log_colors2"):
            g = getattr(model, name).grad
            rec[name + "_grad"] = g.abs().sum().item() if g is not None else None
            if g is not None:
                flat = g.detach().cpu().flatten()
                if device == "cpu":
                    reference[(i, name)] = flat
                elif flat.norm() > 0:
                    ref = reference[(i, name)]
                    rec[name + "_cpu_cosine"] = torch.nn.functional.cosine_similarity(
                        ref, flat, dim=0
                    ).item()
                    rec[name + "_relative_error"] = (flat - ref).norm().item() / ref.norm().item()
        results.append(rec)
        Image.fromarray((out.detach().cpu().numpy().clip(0, 1) * 255).astype("uint8")).save(
            diagnostics / f"portrait_{device}_{i}.png"
        )
print(json.dumps(results, indent=2))
(diagnostics / "portrait_diagnostic.json").write_text(json.dumps(results, indent=2))
