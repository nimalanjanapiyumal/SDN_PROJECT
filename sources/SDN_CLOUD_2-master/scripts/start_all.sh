#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

bash "${PROJECT_ROOT}/scripts/start_observability.sh"
bash "${PROJECT_ROOT}/scripts/start_controller.sh"

if ! wait_for_url "http://127.0.0.1:8080/api/v1/state" 30 1; then
  echo "Controller API not yet ready. Check logs/controller.log"
fi

bash "${PROJECT_ROOT}/scripts/start_policy_agent.sh"

echo "Full stack started."
echo "Launch a traffic scenario with:"
echo "  bash scripts/run_topology.sh --foreground --scenario mixed --cli"
