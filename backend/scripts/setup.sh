#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
if [ ! -x backend/.venv/bin/python ]; then
  uv venv --python 3.10 backend/.venv
fi
backend/.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 10), "Use Python 3.10; existing environment was not replaced"'
uv pip install --python backend/.venv/bin/python -r backend/requirements.lock.txt
