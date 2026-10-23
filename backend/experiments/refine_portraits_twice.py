"""Two bounded CPU color-refinement attempts; never changes upstream or source assets.
Uses fixed checkpoint geometry and Pearl color; this is not geometry retraining.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "external/Auto-MIA"))
import numpy as np
import torch
import trimesh
from PIL import Image
from scipy.ndimage import map_coordinates
from skimage.measure import marching_cubes
from volume_illusion.model import VolumeModel, create_dual_view_cameras
from volume_illusion.renderer import create_volume_renderer


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2))


def make_model(state, resolution):
    model = VolumeModel(
        create_volume_renderer(resolution, n_pts_per_ray=150, device="cpu", orthographic=True),
        volume_size=[128] * 3,
        voxel_size=3 / 128,
        valid_cube_ratio=0.85,
    )
    model.load_state_dict(state)
    model.inner_temperature, model.outer_scale, model.density_bias = 2.25, 0.8, 0.5
    model.log_densities.requires_grad_(False)
    model.log_colors2.requires_grad_(False)
    return model


def targets(job, resolution):
    result = []
    for index in (1, 2):
        image = Image.open(job / f"normalized/input_{index}_rgba.png").convert("RGBA")
        image = image.resize((resolution, resolution), Image.Resampling.LANCZOS)
        array = np.array(image).copy()
        # Make hidden RGB explicitly black; retain alpha for supervision.
        array[array[:, :, 3] == 0, :3] = 0
        rgb = torch.tensor(array[:, :, :3] / 255.0, dtype=torch.float32)
        mask = torch.tensor(array[:, :, 3] > 127)
        result.append((rgb, mask))
    return result


def mesh_export(model, cameras, output):
    # Match Volumes' world axes: raw (D,H,W) maps to world (x,z,y).
    raw = (
        torch.sigmoid(model.inner_temperature * model.log_densities.detach() - model.density_bias)
        * model.outer_scale
        * model.density_scale
        * model.spatial_mask
    )[0].numpy()
    indices, faces, _, _ = marching_cubes(raw, level=0.36)
    vertices = (
        indices[:, [0, 2, 1]] - (np.array(raw.shape)[[0, 2, 1]] - 1) / 2
    ) * model._voxel_size
    # Axis permutation reverses handedness; reverse winding too.
    mesh = trimesh.Trimesh(vertices, faces[:, ::-1], process=False)
    fields = []
    for logits in (model.log_colors1, model.log_colors2):
        field = torch.sigmoid(logits.detach()).numpy()
        fields.append(
            np.stack(
                [map_coordinates(channel, indices.T, order=1, mode="nearest") for channel in field],
                axis=1,
            )
        )
    centers = [camera.get_camera_center().detach().numpy()[0] for camera in cameras]
    directions = [
        (center - vertices) / np.linalg.norm(center - vertices, axis=1, keepdims=True)
        for center in centers
    ]
    scores = [(mesh.vertex_normals * d).sum(axis=1) for d in directions]
    # Static normal-facing bake, not a view-dependent switch or averaged field.
    choose = scores[0] >= scores[1]
    color = np.where(choose[:, None], fields[0], fields[1])
    mesh.visual.vertex_colors = np.column_stack(
        [(color.clip(0, 1) * 255).astype("uint8"), np.full(len(vertices), 255, dtype="uint8")]
    )
    report = {}
    for ext in ("ply", "obj"):
        file = output / f"sculpture.{ext}"
        mesh.export(file)
        loaded = trimesh.load(file, force="mesh", process=False)
        assert np.isfinite(loaded.vertices).all() and len(loaded.faces)
        assert loaded.visual.kind == "vertex", "Export lost vertex colors"
        report[ext] = {
            "vertices": len(loaded.vertices),
            "triangles": len(loaded.faces),
            "watertight": bool(loaded.is_watertight),
            "vertex_colors": True,
        }
    report["limitations"] = (
        "Fixed normal-facing color bake is approximate; no mesh-to-volume visual equivalence or VR validation."
    )
    save_json(output / "mesh-validation.json", report)


def main():
    torch.set_num_threads(4)
    torch.manual_seed(17)
    job = ROOT / "runs/normalized-trials/20261023T220145Z-40fb6c62"
    checkpoint = next(job.glob("*/models/*.pt"))
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)["state_dict"]
    directory = ROOT / "outputs/portrait-repair-two-attempts"
    directory.mkdir(exist_ok=False)
    manifest = {
        "status": "running",
        "attempt_limit": 2,
        "source_checkpoint": str(checkpoint),
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "strategy": "CPU; fixed geometry and Pearl color; reset Mona color then positive foreground L1 only",
        "runtime": {
            "inner_temperature": 2.25,
            "outer_scale": 0.8,
            "density_bias": 0.5,
            "density_scale": 0.9,
            "azimuths": [-45, 45],
            "elevations": [0, 0],
        },
        "seed": 17,
        "torch": torch.__version__,
        "attempts": [],
    }
    # Preserve exact pinned implementation identity and the bounded recipe.
    import subprocess

    manifest["submodule_commit"] = subprocess.check_output(
        ["git", "-C", str(ROOT / "external/Auto-MIA"), "rev-parse", "HEAD"], text=True
    ).strip()
    manifest["input_hashes"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (job / "normalized").glob("*.png")
    }
    save_json(directory / "manifest.json", manifest)
    try:
        for attempt, resolution, steps, lr in [(1, 96, 300, 0.05), (2, 128, 300, 0.015)]:
            start = time.monotonic()
            out = directory / f"attempt-{attempt}"
            out.mkdir()
            model = make_model(state, resolution)
            if attempt == 1:
                with torch.no_grad():
                    model.log_colors1.fill_(float(np.log(0.3 / 0.7)))
            cameras = create_dual_view_cameras(device="cpu", azim1=-45, azim2=45, orthographic=True)
            target = targets(job, resolution)
            for index, (rgb, mask) in enumerate(target, 1):
                Image.fromarray((rgb.numpy() * 255).astype("uint8")).save(
                    out / f"target_{index}_black.png"
                )
            original_pearl = model.log_colors2.detach().clone()
            optimizer = torch.optim.Adam([model.log_colors1], lr=lr)
            record = {
                "attempt": attempt,
                "resolution": resolution,
                "steps": steps,
                "lr": lr,
                "status": "running",
                "warm_start": "reset Mona field" if attempt == 1 else "attempt 1",
            }
            manifest["attempts"].append(record)
            save_json(directory / "manifest.json", manifest)
            for step in range(steps):
                optimizer.zero_grad(set_to_none=True)
                prediction = model(cameras[0])[0, :, :, :3]
                rgb, mask = target[0]
                loss = (prediction - rgb).abs()[mask].mean()
                loss.backward()
                optimizer.step()
                if step % 50 == 0 or step == steps - 1:
                    print(
                        json.dumps(
                            {
                                "attempt": attempt,
                                "step": step,
                                "Mona_MAE": loss.item(),
                                "elapsed_seconds": round(time.monotonic() - start, 1),
                            }
                        ),
                        flush=True,
                    )
            assert torch.equal(original_pearl, model.log_colors2.detach())
            panels = []
            metrics = {}
            with torch.no_grad():
                for index, camera in enumerate(cameras):
                    prediction = model(camera)[0, :, :, :3]
                    rgb, mask = target[index]
                    metrics[str(index + 1)] = float((prediction - rgb).abs()[mask].mean())
                    pixels = (prediction.clamp(0, 1).numpy() * 255).astype("uint8")
                    Image.fromarray(pixels).save(out / f"render_{index + 1}.png")
                    panels.append(pixels)
            Image.fromarray(np.concatenate(panels, axis=1)).save(out / "two_views.png")
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "volume_size": [128] * 3,
                    "voxel_size": 3 / 128,
                    "runtime": manifest["runtime"],
                    "metrics": metrics,
                },
                out / "refined.pt",
            )
            mesh_export(model, cameras, out)
            state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            record.update(
                status="complete",
                per_view_MAE=metrics,
                seconds=time.monotonic() - start,
                pearl_field_unchanged=True,
            )
            save_json(directory / "manifest.json", manifest)
        manifest["status"] = "complete"
        save_json(directory / "manifest.json", manifest)
    except BaseException as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        save_json(directory / "manifest.json", manifest)
        raise


if __name__ == "__main__":
    main()
