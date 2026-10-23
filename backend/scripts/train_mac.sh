#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1
export PYTORCH_ENABLE_MPS_FALLBACK=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/work/matplotlib"
export XDG_CACHE_HOME="$PWD/work/cache"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" runs
exec .venv/bin/python -u external/Auto-MIA/main_enhanced.py \
  --device mps \
  --supervision_image1 "$PWD/assets/input_one/example_rgba.png" \
  --supervision_image2 "$PWD/assets/input_two/example_rgba.png" \
  --volume_size 128 --render_width 64 --render_height 64 \
  --pts_per_ray 64 --n_iter 200 \
  --azim1 0 --azim2 180 --elev1 0 --elev2 0 \
  --output_dir "$PWD/runs" "$@"
