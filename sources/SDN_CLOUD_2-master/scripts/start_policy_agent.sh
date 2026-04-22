#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

ensure_dirs
activate_venv
cd "${PROJECT_ROOT}"

if [[ ! -f "${PROJECT_ROOT}/ml/models/classifier.joblib" || ! -f "${PROJECT_ROOT}/ml/models/sla_regressor.joblib" ]]; then
  python ml/train_models.py --samples 1500
fi

CMD=(
  python ml/policy_agent.py
  --prometheus-url http://127.0.0.1:9090
  --controller-url http://127.0.0.1:8080
  --metrics-port 9102
)
LOG_FILE="${PROJECT_ROOT}/logs/policy_agent.log"
PID_FILE="${PROJECT_ROOT}/run/policy_agent.pid"

if [[ "${1:-}" == "--foreground" ]]; then
  exec "${CMD[@]}"
fi

nohup "${CMD[@]}" >"${LOG_FILE}" 2>&1 &
echo $! >"${PID_FILE}"

if wait_for_url "http://127.0.0.1:9102/metrics" 30 1; then
  echo "Policy agent started. Metrics: http://127.0.0.1:9102/metrics"
else
  echo "Policy agent launched, but metrics endpoint is not ready yet. Check ${LOG_FILE}"
fi
