#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
bash manage.sh controller bootstrap
bash manage.sh dashboard bootstrap
bash manage.sh controller start
sleep 2
export CONTROLLER_API_URL="${CONTROLLER_API_URL:-http://127.0.0.1:8080}"
bash manage.sh dashboard start
echo "[OK] Controller and dashboard started."
