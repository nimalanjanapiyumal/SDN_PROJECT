#!/usr/bin/env bash
set -euo pipefail

SCENARIO="${1:-mixed}"
DURATION="${2:-90}"
MODE="${3:-cli}"
LINK_MODE="${4:-basic}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RYU_APP="$REPO_ROOT/src/adaptive_cloud_platform/sdn/ryu_integrated_app.py"
TOPOLOGY="$REPO_ROOT/src/topology/adaptive_cloud_topology.py"
CONTROLLER_PORT="${ADAPTIVE_CONTROLLER_PORT:-6653}"
RYU_LOG="${ADAPTIVE_RYU_LOG:-$REPO_ROOT/logs/ryu_integrated.log}"
mkdir -p "$(dirname "$RYU_LOG")"

command -v ryu-manager >/dev/null 2>&1 || { echo "ryu-manager is required. Install Ryu in Ubuntu/WSL/Linux first."; exit 1; }
command -v mn >/dev/null 2>&1 || { echo "Mininet is required. Install mininet and Open vSwitch first."; exit 1; }

export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
export ADAPTIVE_API_URL="${ADAPTIVE_API_URL:-http://127.0.0.1:8080}"
export ADAPTIVE_RULE_SYNC_INTERVAL="${ADAPTIVE_RULE_SYNC_INTERVAL:-5}"

echo "Starting Ryu controller with integrated rule sync: $RYU_APP"
ryu-manager --observe-links --ofp-tcp-listen-port "$CONTROLLER_PORT" "$RYU_APP" >"$RYU_LOG" 2>&1 &
RYU_PID="$!"

cleanup() {
  echo "Stopping Ryu controller"
  kill "$RYU_PID" >/dev/null 2>&1 || true
  sudo mn -c >/dev/null 2>&1 || true
}
trap cleanup EXIT

python3 - <<PY
import socket
import sys
import time

deadline = time.time() + 12
last_error = None
while time.time() < deadline:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.connect(("127.0.0.1", int("$CONTROLLER_PORT")))
        sock.close()
        sys.exit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(0.5)
    finally:
        sock.close()
print(f"Ryu controller failed to open port $CONTROLLER_PORT: {last_error}", file=sys.stderr)
sys.exit(1)
PY

if ! kill -0 "$RYU_PID" >/dev/null 2>&1; then
  echo "Ryu controller exited before Mininet startup. Recent log output:"
  tail -n 80 "$RYU_LOG" || true
  exit 1
fi

echo "Launching Mininet scenario '$SCENARIO' for ${DURATION}s using link mode '$LINK_MODE'"
TOPO_ARGS=(--controller-ip 127.0.0.1 --controller-port "$CONTROLLER_PORT" --scenario "$SCENARIO" --duration "$DURATION" --link-mode "$LINK_MODE")
if [[ "$MODE" == "cli" ]]; then
  TOPO_ARGS+=(--cli)
else
  TOPO_ARGS+=(--foreground)
fi
sudo -E python3 "$TOPOLOGY" \
  "${TOPO_ARGS[@]}"
