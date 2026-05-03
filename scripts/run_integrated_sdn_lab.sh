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

command -v mn >/dev/null 2>&1 || { echo "Mininet is required. Install mininet and Open vSwitch first."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required."; exit 1; }

if ! command -v ryu-manager >/dev/null 2>&1; then
  if ! python3 - <<'PY' >/dev/null 2>&1
import ryu  # noqa: F401
PY
  then
    echo "Ryu is required. Install ryu-manager or the Python ryu package first."
    exit 1
  fi
fi

export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
export ADAPTIVE_API_URL="${ADAPTIVE_API_URL:-http://127.0.0.1:8080}"
export ADAPTIVE_RULE_SYNC_INTERVAL="${ADAPTIVE_RULE_SYNC_INTERVAL:-5}"
export EVENTLET_NO_GREENDNS="${EVENTLET_NO_GREENDNS:-yes}"

echo "Validating integrated Ryu controller app syntax"
python3 -m py_compile "$RYU_APP"

echo "Validating integrated Ryu controller imports"
python3 - <<PY
import importlib.util
import sys

app_path = "$RYU_APP"
spec = importlib.util.spec_from_file_location("adaptive_cloud_platform.sdn.ryu_integrated_app", app_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
controller = getattr(module, "IntegratedAdaptiveCloudController", None)
if controller is None:
    raise SystemExit("IntegratedAdaptiveCloudController class not found")
print(f"Loaded controller class: {controller.__name__}")
PY

if command -v ss >/dev/null 2>&1; then
  if ss -ltn "( sport = :$CONTROLLER_PORT )" | grep -q ":$CONTROLLER_PORT"; then
    echo "Warning: port $CONTROLLER_PORT is already in use before starting Ryu"
    ss -ltnp "( sport = :$CONTROLLER_PORT )" || true
  fi
fi

echo "Starting Ryu controller with integrated rule sync: $RYU_APP"
if python3 - <<'PY' >/dev/null 2>&1
import ryu  # noqa: F401
PY
then
  CONTROLLER_CMD=(python3 -m ryu.cmd.manager --verbose --observe-links --ofp-tcp-listen-port "$CONTROLLER_PORT" "$RYU_APP")
else
  CONTROLLER_CMD=(ryu-manager --verbose --observe-links --ofp-tcp-listen-port "$CONTROLLER_PORT" "$RYU_APP")
fi
"${CONTROLLER_CMD[@]}" >"$RYU_LOG" 2>&1 &
RYU_PID="$!"

cleanup() {
  echo "Stopping Ryu controller"
  kill "$RYU_PID" >/dev/null 2>&1 || true
  sudo mn -c >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! python3 - <<PY
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
then
  echo "Controller startup failed. Recent Ryu log output:"
  tail -n 120 "$RYU_LOG" || true
  exit 1
fi

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
