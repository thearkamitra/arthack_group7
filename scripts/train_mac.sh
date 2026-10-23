#!/usr/bin/env bash
# Compatibility entry point for the original upstream-style arguments.
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash backend/scripts/train_mac.sh "$@"
