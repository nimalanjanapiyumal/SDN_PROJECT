#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

ensure_dirs
activate_venv
cd "${PROJECT_ROOT}"

SCENARIO="mixed"
DURATION="${DURATION:-90}"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario)
      SCENARIO="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --cli|--foreground)
      ARGS+=("$1")
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

CMD=(
  "${PROJECT_ROOT}/.venv/bin/python"
  topology/adaptive_cloud_topology.py
  --controller-ip 127.0.0.1
  --controller-port 6653
  --scenario "${SCENARIO}"
  --duration "${DURATION}"
  "${ARGS[@]}"
)

if printf '%s
' "${ARGS[@]}" | grep -q -- '--foreground\|--cli'; then
  exec sudo env "PATH=${PATH}" "${CMD[@]}"
fi

LOG_FILE="${PROJECT_ROOT}/logs/mininet.log"
PID_FILE="${PROJECT_ROOT}/run/mininet.pid"
nohup sudo env "PATH=${PATH}" "${CMD[@]}" >"${LOG_FILE}" 2>&1 &
echo $! >"${PID_FILE}"
echo "Topology launched in background. Log: ${LOG_FILE}"
