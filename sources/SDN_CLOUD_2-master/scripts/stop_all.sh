#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

stop_pidfile "${PROJECT_ROOT}/run/policy_agent.pid"
stop_pidfile "${PROJECT_ROOT}/run/controller.pid"
stop_pidfile "${PROJECT_ROOT}/run/mininet.pid"

bash "${PROJECT_ROOT}/scripts/clean_mininet.sh" || true

cd "${PROJECT_ROOT}"
compose down || true

echo "Stopped controller, policy agent, Mininet, Prometheus, and Grafana."
