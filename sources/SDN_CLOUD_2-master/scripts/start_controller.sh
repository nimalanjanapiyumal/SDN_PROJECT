#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

ensure_dirs
activate_venv
cd "${PROJECT_ROOT}"

CMD=(python scripts/ryu_manager_wrapper.py --observe-links controller/adaptive_controller.py)
LOG_FILE="${PROJECT_ROOT}/logs/controller.log"
PID_FILE="${PROJECT_ROOT}/run/controller.pid"

if [[ "${1:-}" == "--foreground" ]]; then
  exec "${CMD[@]}"
fi

nohup "${CMD[@]}" >"${LOG_FILE}" 2>&1 &
echo $! >"${PID_FILE}"

if wait_for_url "http://127.0.0.1:9101/metrics" 30 1; then
  echo "Controller started. Metrics: http://127.0.0.1:9101/metrics"
else
  echo "Controller process launched, but metrics endpoint is not ready yet. Check ${LOG_FILE}"
fi
