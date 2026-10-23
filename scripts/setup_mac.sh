#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash backend/scripts/setup_mac.sh "$@"
