"""Build a new static surface from normalized masks; no training."""

import argparse
from pathlib import Path

from borrowed_eyes.surface_bake import build_surface

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-one", type=Path, required=True)
    parser.add_argument("--image-two", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build_surface(args.image_one, args.image_two, args.output))
