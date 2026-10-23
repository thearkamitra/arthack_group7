# Project conventions

Read this file before changing the project and follow it for all future work.

## Boundaries and layout
- Keep application Python, dependency specifications, setup scripts and tests
  under `backend/`. Keep user inputs in `assets/`, deliverables in `outputs/`,
  generated runs in `runs/`, and caches and scratch files in `work/`.
- Keep Auto-MIA at `external/Auto-MIA` as a pinned Git submodule. Do not copy
  or edit upstream code without an explicit reason and documented change.
- Reuse the root `.venv` and Python 3.10. Do not silently replace the environment.
- Keep Unity/frontend code separate when introduced. Do not introduce a web
  framework or service infrastructure until needed.

## Implementation
- Separate image preprocessing, upstream process orchestration, and mesh
  validation. Use typed functions, pathlib, explicit configuration and small
  modules. CLI commands should call reusable functions.
- Never overwrite source images or existing runs. Produce real RGBA PNG files;
  JPEG cannot hold alpha. Preserve RGB pixels when computing segmentation masks.
- Validate inputs before starting expensive work. Use argument lists rather
  than shell command strings. Propagate process failures and retain logs.
- Write a manifest with input hashes, parameters, submodule commit, commands,
  status and output locations for each pipeline run. Mark failures explicitly.
- Pin direct dependencies and record an environment snapshot after installation.
  Keep model downloads/cache locations explicit; do not commit model weights.
- Do not present MLX installation as an MLX port. Distinguish CPU, native MPS,
  MPS with CPU fallback, and MLX. Preserve MPS memory safeguards.
- Document export limitations, including averaged directional colors and
  conversion density logic. File validation is not visual/VR validation.

## Verification and communication
- Test meaningful behavior: preservation of sources/RGB, input rejection,
  failure handling, metadata, and reloading exported geometry.
- Run unit tests without network or model downloads; integration checks must
  be explicit and bounded. Use small renders, not an unrequested full run.
- Keep docs and runnable commands consistent. Report checks actually run and
  material limits. Never claim a training/export job succeeded from exit status
  alone: check its expected artifacts.
- Keep credentials, caches, environments, logs, and generated training data out
  of Git. Avoid unrelated changes and destructive Git operations.
