# Backend guide

Run commands from the repository root with `bash backend/scripts/run.sh`.
This is a local processing CLI, not a web service. Commands call reusable
functions in `borrowed_eyes/`; future Unity adapters can reuse those functions.

## Environment

`bash backend/scripts/setup_mac.sh` creates/reuses the root Python 3.10 `.venv`,
installs pinned Mac dependencies, builds PyTorch3D 0.7.8 from commit
`75ebeeaea0908c5527e7b1e305fbc7681382db47`, and records the environment snapshot.
Apple Command Line Tools and uv are required. The build uses four workers and
`CFLAGS=-Wno-invalid-specialization` for older PyTorch headers with newer Clang.

Direct pins are in `requirements-macos.txt`. `requirements-macos.lock.txt` is
an installed environment snapshot, not a cross-platform lock. For matching
transitive versions, add `-c backend/requirements-macos.lock.txt` to setup's
first install command. `requirements-dev.txt` pins optional lint tooling.

## Supported image-to-surface workflow

```sh
# Optional: create a new transparent cutout from a JPEG.
bash backend/scripts/run.sh remove-background assets/input_one/example.jpg \
  --output work/mona-rgba.png

# Normalize both RGBA images before construction.
bash backend/scripts/run.sh normalize \
  --image-one assets/input_one/example_rgba.png \
  --image-two assets/input_two/example_rgba.png \
  --output work/normalized

# Construct a static mesh, without training.
bash backend/scripts/run.sh bake-surface \
  --image-one work/normalized/input_1_rgba.png \
  --image-two work/normalized/input_2_rgba.png \
  --output outputs/sculpture
```

Segmentation uses rembg/ONNX Runtime CPU with `u2net_human_seg`. Model weights
are downloaded to `work/models/` on first use. No image upload or API key is
needed. `--model u2net` and `--model u2netp` select alternative local models.
Segmentation retains RGB pixels and changes alpha; inspect hair/headwear edges.
The included example RGBA files were made earlier with imagegen; they are not
claimed as outputs of rembg. See `assets/README.md`.

Normalization crops to alpha > 127, matches foreground widths, preserves aspect
ratio and centers on equal transparent canvases. `--size` defaults to 128.
Source files are unchanged; derived pixels are resampled. Output metadata
records crops, dimensions and offsets.

Surface construction intersects both silhouettes in a 128-cubed grid and
bakes fixed projection colors onto surface regions. `--resolution` accepts
16–256. Cameras use azimuth -45/+45 degrees, elevation zero and a 3-unit plane.
It does not reuse optimized Auto-MIA geometry or directional colors. The
manifest records input hashes, settings, implementation/environment hashes,
command and export validation. PLY and OBJ are reloaded to check geometry and
colors. Failed newly created jobs retain explicit failure metadata.

`mesh_preview.render_mesh` rasterizes saved triangles and vertex colors on CPU
for validation. Target-view agreement is an in-sample check. Intermediate views
can stretch or overlap portraits; the back remains abstract. Vertex splits at
color seams mean indexed geometry is not watertight, although welding positions
closes the surface. No printability, stereo VR, arbitrary-pair quality or headset
performance guarantee is made.

## Experimental Auto-MIA pipeline

```sh
bash backend/scripts/run.sh pipeline --prepared --normalize \
  --image-one assets/input_one/example_rgba.png \
  --image-two assets/input_two/example_rgba.png \
  --device cpu --volume-size 128 --width 128 --height 128 \
  --samples 150 --iterations 1200 --azim1 -45 --azim2 45
```

This is an explicit expensive training command, not required for the fixed mesh.
Omit `--prepared` to segment raw inputs. New jobs under `runs/` retain input
hashes, normalization metadata, parameters, submodule commit, logs, exact process
commands, checkpoint and validated mesh outputs. `train` and `export` are also
available separately; use `--help` for their required arguments. Only load trusted
checkpoints. Existing outputs are not overwritten.

The upstream trainer requires 128 or 256 voxels per axis. MPS uses CPU fallback
for 3D grid sampling, and gradient discrepancies were observed against CPU.
MLX is available independently but does not accelerate this code automatically.
48 GB unified memory is shared with the OS; keep MPS safeguards enabled.

The upstream export averages directional colors, reconstructs density differently,
adapts thresholds and can report smoothing warnings. Good volume renders do
not guarantee good exported surface appearance. A Linux/CUDA machine can run
upstream's `environment.yml` for further research; no equivalent Mac speed is
promised. Historical run-specific diagnostics and the two bounded color-repair
attempts are kept in `experiments/`, not in the supported CLI.

## Verification

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
uv pip check --python .venv/bin/python
uvx --from ruff==0.14.1 ruff check --config backend/pyproject.toml backend scripts
uvx --from ruff==0.14.1 ruff format --check --config backend/pyproject.toml backend scripts
```

Unit tests require no network or model downloads. `scripts/check_mac.py` checks
rendering and gradients on CPU/MPS plus MLX availability; it needs local Metal
access and is separate from unit tests. Root `scripts/` entries are compatibility
wrappers. Generated data, weights, credentials, logs and environments stay out
of Git. Do not modify the pinned upstream implementation casually.
