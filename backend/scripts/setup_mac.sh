#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
uv venv --python 3.10 --allow-existing .venv
uv pip install --python .venv/bin/python -r backend/requirements-macos.txt
MAX_JOBS=4 CC=clang CXX=clang++ CFLAGS=-Wno-invalid-specialization \
  uv pip install --python .venv/bin/python --no-build-isolation \
  'git+https://github.com/facebookresearch/pytorch3d.git@75ebeeaea0908c5527e7b1e305fbc7681382db47'
uv pip freeze --python .venv/bin/python > backend/requirements-macos.lock.txt
