#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
export PYTHONPATH=backend
exec backend/.venv/bin/python -m inner_landscape "$@"
