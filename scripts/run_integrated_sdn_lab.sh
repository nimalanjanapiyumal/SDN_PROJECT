#!/usr/bin/env bash
set -euo pipefail

SCENARIO="${1:-mixed}"
DURATION="${2:-90}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RYU_APP="$REPO_ROOT/src/adaptive_cloud_platform/sdn/ryu_integrated_app.py"
TOPOLOGY="$REPO_ROOT/src/topology/adaptive_cloud_topology.py"

command -v ryu-manager >/dev/null 2>&1 || { echo "ryu-manager is required. Install Ryu in Ubuntu/WSL/Linux first."; exit 1; }
command -v mn >/dev/null 2>&1 || { echo "Mininet is required. Install mininet and Open vSwitch first."; exit 1; }

export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
export ADAPTIVE_API_URL="${ADAPTIVE_API_URL:-http://127.0.0.1:8080}"
export ADAPTIVE_RULE_SYNC_INTERVAL="${ADAPTIVE_RULE_SYNC_INTERVAL:-5}"

RYU_LOG="/tmp/adaptive_ryu_integrated.log"
echo "Starting Ryu controller with integrated rule sync: $RYU_APP"
ryu-manager --observe-links "$RYU_APP" >"$RYU_LOG" 2>&1 &
RYU_PID="$!"

cleanup() {
  echo "Stopping Ryu controller"
  kill "$RYU_PID" >/dev/null 2>&1 || true
  sudo mn -c >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 3
echo "Launching Mininet scenario '$SCENARIO' for ${DURATION}s"
sudo -E python3 "$TOPOLOGY" \
  --controller-ip 127.0.0.1 \
  --controller-port 6653 \
  --scenario "$SCENARIO" \
  --duration "$DURATION" \
  --cli

