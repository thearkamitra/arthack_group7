# Borrowed Eyes: Museum of Perspectives

One fixed sculpture reveals Mona Lisa from one viewpoint and Girl with a
Pearl Earring from another. Move between them to see the images stretch and
overlap. This repository contains the local Python backend for preparing
image pairs, constructing colored meshes, and experimenting with Auto-MIA.

## Current approach

The working MeshLab prototype uses **two-view silhouette intersection and
fixed projection colors**. It needs no training or runtime texture switching.
This is a separate construction method from the experimental Auto-MIA volume
optimizer. Target-view checks achieved silhouette overlap above 98%; back
views remain abstract color bands. Stereo VR and arbitrary pairs are unvalidated.

## Setup on Apple Silicon

Install uv and Apple Command Line Tools, then:

```sh
git clone --recurse-submodules https://github.com/thearkamitra/arthack_group7.git
cd arthack_group7
bash backend/scripts/setup_mac.sh
```

Setup reuses a root `.venv` with native Python 3.10. Scientific dependencies
are pinned under `backend/`. PyTorch3D builds from a pinned source commit;
setup limits build workers and applies a scoped compatibility flag for newer
Apple Clang. See [backend instructions](backend/README.md) for details.

## Build the example mesh

The supplied JPEG originals and RGBA derivatives are in `assets/`. Preserve
originals and always choose a new output directory:

```sh
bash backend/scripts/run.sh normalize \
  --image-one assets/input_one/example_rgba.png \
  --image-two assets/input_two/example_rgba.png \
  --output work/example-normalized

bash backend/scripts/run.sh bake-surface \
  --image-one work/example-normalized/input_1_rgba.png \
  --image-two work/example-normalized/input_2_rgba.png \
  --output outputs/example-sculpture
```

Open `outputs/example-sculpture/sculpture.ply` in MeshLab with vertex colors
visible. Mona Lisa resolves at azimuth -45 degrees, Pearl at +45 degrees,
elevation zero, around the Y axis. The construction uses orthographic views
and a centered 3-unit viewing plane. OBJ is also exported, but its vertex-color
extension is not supported by every viewer. Color seams split some indices;
the position-welded surface is closed, but the indexed mesh is not print-ready.

For new JPEGs, use the `remove-background` command before normalization.
Local segmentation downloads weights on first use; it does not upload images.
The [backend guide](backend/README.md) also covers experimental training,
mesh export, validation, and known rendering limits.

## Layout

```text
backend/       Reusable Python modules, CLI, setup, tests and experiments
assets/        Sample inputs and provenance
external/      Auto-MIA Git submodule (pinned, unchanged)
outputs/       Generated deliverables; ignored by Git
runs/          Generated training jobs; ignored by Git
work/          Caches, downloaded weights and scratch files; ignored by Git
scripts/       Compatibility wrappers for the original setup/check commands
```

Auto-MIA is pinned at `external/Auto-MIA`. After a normal clone, initialize it
with `git submodule update --init --recursive`. Generated outputs and local
experiment checkpoints are intentionally not shipped; regenerate the mesh
with the commands above.

## Checks

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
uv pip check --python .venv/bin/python
uvx --from ruff==0.14.1 ruff check --config backend/pyproject.toml backend scripts
uvx --from ruff==0.14.1 ruff format --check --config backend/pyproject.toml backend scripts
```

MLX is installed for independent experiments. Auto-MIA is PyTorch/PyTorch3D
code, not an MLX port. Its native MPS path lacks 3D grid sampling; CPU fallback
renders successfully, but CPU/MPS gradient differences were observed. The
fixed-surface workflow runs on CPU and avoids that training path.

Project conventions are in [AGENTS.md](AGENTS.md). Input provenance is in
[assets/README.md](assets/README.md).
