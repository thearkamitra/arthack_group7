"""Run with PYTHONPATH=backend .venv/bin/python -m borrowed_eyes."""

import argparse
import subprocess
from pathlib import Path

from .images import remove_background
from .workflow import ROOT, TrainingConfig, export_mesh, pipeline, train


def main() -> None:
    parser = argparse.ArgumentParser(description="Borrowed Eyes local processing backend")
    commands = parser.add_subparsers(dest="command", required=True)
    bg = commands.add_parser("remove-background")
    bg.add_argument("input", type=Path)
    bg.add_argument("--output", type=Path, required=True)
    bg.add_argument(
        "--model", choices=["u2net_human_seg", "u2net", "u2netp"], default="u2net_human_seg"
    )
    normalize = commands.add_parser("normalize", help="Align an RGBA image pair without training")
    normalize.add_argument("--image-one", type=Path, required=True)
    normalize.add_argument("--image-two", type=Path, required=True)
    normalize.add_argument("--output", type=Path, required=True)
    normalize.add_argument("--size", type=int, default=128)
    surface = commands.add_parser(
        "bake-surface",
        help="Build a fixed two-view silhouette mesh with projected colors; no training",
    )
    surface.add_argument("--image-one", type=Path, required=True)
    surface.add_argument("--image-two", type=Path, required=True)
    surface.add_argument("--output", type=Path, required=True)
    surface.add_argument("--resolution", type=int, default=128)
    export = commands.add_parser("export")
    export.add_argument("checkpoint", type=Path)
    export.add_argument(
        "--output", type=Path, required=True, help="New directory for OBJ, PLY and logs"
    )
    for name in ("train", "pipeline"):
        sub = commands.add_parser(name)
        sub.add_argument("--image-one", type=Path, required=True)
        sub.add_argument("--image-two", type=Path, required=True)
        sub.add_argument("--output", type=Path, default=ROOT / "runs")
        sub.add_argument("--device", choices=["cpu", "mps", "cuda"], default="mps")
        sub.add_argument("--volume-size", type=int, choices=[128, 256], default=128)
        for flag, default in [("width", 64), ("height", 64), ("samples", 64), ("iterations", 200)]:
            sub.add_argument(f"--{flag}", type=int, default=default)
        for flag, default in [("azim1", 0.0), ("azim2", 180.0), ("elev1", 0.0), ("elev2", 0.0)]:
            sub.add_argument(f"--{flag}", type=float, default=default)
        if name == "pipeline":
            sub.add_argument(
                "--normalize",
                action="store_true",
                help="Match foreground widths on square canvases without stretching",
            )
            sub.add_argument(
                "--prepared", action="store_true", help="Inputs are already transparent RGBA PNGs"
            )
            sub.add_argument(
                "--model", choices=["u2net_human_seg", "u2net", "u2netp"], default="u2net_human_seg"
            )
    args = parser.parse_args()
    try:
        if args.command == "remove-background":
            print(remove_background(args.input, args.output, ROOT / "work/models", args.model))
        elif args.command == "normalize":
            from .normalize import normalize_pair

            print(normalize_pair(args.image_one, args.image_two, args.output, args.size))
        elif args.command == "bake-surface":
            from .surface_bake import build_surface

            print(build_surface(args.image_one, args.image_two, args.output, args.resolution))
        elif args.command == "export":
            print(export_mesh(args.checkpoint, args.output.resolve()))
        else:
            config = TrainingConfig(
                **{name: getattr(args, name) for name in TrainingConfig.__dataclass_fields__}
            )
            if args.command == "pipeline":
                print(
                    pipeline(
                        args.image_one,
                        args.image_two,
                        args.output,
                        config,
                        args.prepared,
                        args.model,
                        args.normalize,
                    )
                )
            else:
                print(train(args.image_one, args.image_two, args.output, config))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
