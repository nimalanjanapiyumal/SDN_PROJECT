#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT_DIR/.venv-dashboard/bin/activate"
export CONTROLLER_API_URL="${CONTROLLER_API_URL:-http://127.0.0.1:8080}"
bash "$ROOT_DIR/dashboard/run_dashboard.sh"
