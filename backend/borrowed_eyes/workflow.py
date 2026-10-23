"""Orchestrate the pinned upstream code without modifying the submodule."""

import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .images import remove_background, validate_rgba

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "external" / "Auto-MIA"


@dataclass(frozen=True)
class TrainingConfig:
    device: str = "mps"
    volume_size: int = 128
    width: int = 64
    height: int = 64
    samples: int = 64
    iterations: int = 200
    azim1: float = 0.0
    azim2: float = 180.0
    elev1: float = 0.0
    elev2: float = 0.0

    def validate(self) -> None:
        if self.device not in ("cpu", "mps", "cuda"):
            raise ValueError("Device must be cpu, mps, or cuda")
        if self.volume_size not in (128, 256):
            raise ValueError("Upstream training requires 128 or 256 voxels per axis")
        if min(self.width, self.height, self.samples, self.iterations) <= 0:
            raise ValueError("Dimensions, samples, and iterations must be positive")
        if not all(
            math.isfinite(angle) for angle in (self.azim1, self.azim2, self.elev1, self.elev2)
        ):
            raise ValueError("Camera angles must be finite")


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTORCH_ENABLE_MPS_FALLBACK="1",
        MPLBACKEND="Agg",
        MPLCONFIGDIR=str(ROOT / "work/matplotlib"),
        XDG_CACHE_HOME=str(ROOT / "work/cache"),
    )
    for key in ("MPLCONFIGDIR", "XDG_CACHE_HOME"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env


def execute(command: list[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("x") as stream:
        log.with_suffix(".command.json").write_text(json.dumps(command, indent=2))
        subprocess.run(
            command,
            cwd=ROOT,
            env=environment(),
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=True,
        )


def train(one: Path, two: Path, output: Path, config: TrainingConfig) -> Path:
    config.validate()
    for image in (one, two):
        validate_rgba(image)
    command = [
        sys.executable,
        "-u",
        str(UPSTREAM / "main_enhanced.py"),
        "--supervision_image1",
        str(one.resolve()),
        "--supervision_image2",
        str(two.resolve()),
        "--output_dir",
        str(output.resolve()),
    ]
    flags = {
        "device": "device",
        "volume_size": "volume_size",
        "width": "render_width",
        "height": "render_height",
        "samples": "pts_per_ray",
        "iterations": "n_iter",
        "azim1": "azim1",
        "azim2": "azim2",
        "elev1": "elev1",
        "elev2": "elev2",
    }
    command += [
        value for key, flag in flags.items() for value in (f"--{flag}", str(getattr(config, key)))
    ]
    before = set(output.glob("binary_voxel_*/models/*.pt"))
    execute(command, output / "training.log")
    checkpoints = set(output.glob("binary_voxel_*/models/*.pt")) - before
    if len(checkpoints) != 1:
        raise RuntimeError(f"Expected one new training checkpoint; found {len(checkpoints)}")
    return checkpoints.pop()


def export_mesh(checkpoint: Path, output: Path) -> dict:
    import torch

    # Only load checkpoints generated locally or from a trusted source.
    data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    spacing = float(data["voxel_size"])
    if not spacing > 0:
        raise ValueError("Checkpoint voxel spacing must be positive")
    output.mkdir(parents=True, exist_ok=False)
    execute(
        [
            sys.executable,
            str(UPSTREAM / "volume_to_mesh.py"),
            "--volume_path",
            str(checkpoint.resolve()),
            "--output_path",
            str(output / "sculpture.obj"),
            "--voxel_size",
            str(spacing),
            "--threshold",
            "0.5",
        ],
        output / "export.log",
    )
    result = validate_meshes(output)
    result["appearance_limit"] = (
        "Directional color fields are averaged; renderer equivalence is not verified."
    )
    result["export_warnings"] = [
        line.strip()
        for line in (output / "export.log").read_text().splitlines()
        if "failed" in line.lower() or "warning" in line.lower()
    ]
    (output / "validation.json").write_text(json.dumps(result, indent=2))
    return result


def validate_meshes(output: Path) -> dict:
    import numpy as np
    import trimesh

    result = {}
    for extension in ("obj", "ply"):
        path = output / f"sculpture.{extension}"
        mesh = trimesh.load(path, force="mesh", process=False)
        if not len(mesh.vertices) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
            raise ValueError(f"Empty or nonfinite geometry in {path}")
        result[extension] = {
            "path": str(path),
            "vertices": len(mesh.vertices),
            "triangles": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "vertex_colors": mesh.visual.kind == "vertex",
        }
    return result


def input_record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def pipeline(
    one: Path,
    two: Path,
    output: Path,
    config: TrainingConfig,
    prepared: bool = False,
    model: str = "u2net_human_seg",
    normalize: bool = False,
) -> Path:
    config.validate()
    if normalize and (config.width != config.height or config.width > config.volume_size):
        raise ValueError("Normalized trial needs square renders no larger than the voxel grid")
    # Check both files before downloads or training.
    for image in (one, two):
        from PIL import Image

        with Image.open(image) as opened:
            opened.verify()
    job = output.resolve() / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    job.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "running",
        "inputs": [input_record(one), input_record(two)],
        "config": asdict(config),
        "prepared": prepared,
        "segmentation_model": None if prepared else model,
        "commands": "See training.command.json and meshes/export.command.json",
        "python": sys.version,
        "submodule_commit": subprocess.check_output(
            ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True
        ).strip(),
        "appearance_limit": "Upstream export averages directional colors and uses conversion-specific density logic.",
    }
    manifest_path = job / "manifest.json"

    def save() -> None:
        temporary = manifest_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(manifest, indent=2))
        temporary.replace(manifest_path)

    save()
    print(f"Job: {job}", flush=True)
    try:
        if not prepared:
            one = remove_background(
                one, job / "inputs/input_one_rgba.png", ROOT / "work/models", model
            )
            two = remove_background(
                two, job / "inputs/input_two_rgba.png", ROOT / "work/models", model
            )
        if normalize:
            from .normalize import normalize_pair

            one, two = normalize_pair(one, two, job / "normalized", config.width)
            manifest["normalization"] = json.loads(
                (job / "normalized/normalization.json").read_text()
            )
        manifest["training_inputs"] = [input_record(one), input_record(two)]
        manifest["environment_snapshot"] = input_record(
            ROOT / "backend/requirements-macos.lock.txt"
        )
        if not prepared:
            manifest["segmentation_weights"] = input_record(ROOT / "work/models" / f"{model}.onnx")
        save()
        checkpoint = train(one, two, job, config)
        manifest["checkpoint"] = str(checkpoint)
        manifest["checkpoint_sha256"] = input_record(checkpoint)["sha256"]
        manifest["status"] = "exporting"
        save()
        manifest["meshes"] = export_mesh(checkpoint, job / "meshes")
        manifest["status"] = "complete"
        save()
        return job
    except (Exception, KeyboardInterrupt) as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        save()
        raise
