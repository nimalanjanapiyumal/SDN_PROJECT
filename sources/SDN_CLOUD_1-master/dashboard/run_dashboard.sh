#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DASHBOARD_PORT="${DASHBOARD_PORT:-5050}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
export PYTHONPATH="$ROOT_DIR/vm-a1-controller:${PYTHONPATH:-}"
cd "$SCRIPT_DIR/flask_dashboard"
python3 app.py
