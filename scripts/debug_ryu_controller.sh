#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-verify}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RYU_APP="$REPO_ROOT/src/adaptive_cloud_platform/sdn/ryu_integrated_app.py"
CONTROLLER_PORT="${ADAPTIVE_CONTROLLER_PORT:-6653}"
RYU_LOG="${ADAPTIVE_RYU_LOG:-$REPO_ROOT/logs/ryu_integrated.log}"
mkdir -p "$(dirname "$RYU_LOG")"

echo "[1/7] Runtime"
echo "repo: $REPO_ROOT"
echo "python3: $(command -v python3 || echo missing)"
echo "ryu-manager: $(command -v ryu-manager || echo missing)"
echo "mn: $(command -v mn || echo missing)"
echo "ovs-vsctl: $(command -v ovs-vsctl || echo missing)"
echo "controller port: $CONTROLLER_PORT"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }

echo "[2/7] Ryu availability"
RYU_RUNTIME="missing"
if python3 - <<'PY' >/dev/null 2>&1
import ryu  # noqa: F401
PY
then
  echo "Python ryu module found"
  RYU_RUNTIME="python-module"
elif command -v ryu-manager >/dev/null 2>&1; then
  echo "ryu-manager wrapper found"
  RYU_RUNTIME="wrapper"
else
  echo "Ryu is not installed. Install ryu-manager or python3 -m pip install ryu"
  exit 1
fi

echo "[3/7] Controller app syntax"
python3 -m py_compile "$RYU_APP"

echo "[4/7] Controller app imports"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
export EVENTLET_NO_GREENDNS="${EVENTLET_NO_GREENDNS:-yes}"
export ADAPTIVE_RYU_COMPAT="${ADAPTIVE_RYU_COMPAT:-1}"
if [[ "$RYU_RUNTIME" == "python-module" ]]; then
python3 - <<PY
import importlib.util
app_path = "$RYU_APP"
spec = importlib.util.spec_from_file_location("adaptive_cloud_platform.sdn.ryu_integrated_app", app_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print("loaded:", getattr(module, "IntegratedAdaptiveCloudController").__name__)
PY
else
  echo "skipped: active python3 does not provide the ryu module; wrapper runtime will be tested in step 7"
fi

echo "[5/7] API reachability"
python3 - <<'PY'
import os
import urllib.request

api_url = os.environ.get("ADAPTIVE_API_URL", "http://127.0.0.1:8080").rstrip("/")
try:
    with urllib.request.urlopen(f"{api_url}/healthz", timeout=2.0) as response:
        print("api:", response.status, api_url)
except Exception as exc:
    print(f"api warning: {api_url} is not reachable yet -> {exc}")
PY

echo "[6/7] Port pre-check"
if command -v ss >/dev/null 2>&1; then
  if ss -ltn "( sport = :$CONTROLLER_PORT )" | grep -q ":$CONTROLLER_PORT"; then
    echo "port $CONTROLLER_PORT is already in use"
    ss -ltnp "( sport = :$CONTROLLER_PORT )" || true
    exit 1
  fi
else
  echo "ss not available; skipping socket pre-check"
fi

echo "[7/7] Start controller"
if [[ "$RYU_RUNTIME" == "python-module" ]]; then
  CONTROLLER_CMD=(python3 -m ryu.cmd.manager --verbose --observe-links --ofp-tcp-listen-port "$CONTROLLER_PORT" "$RYU_APP")
else
  CONTROLLER_CMD=(ryu-manager --verbose --observe-links --ofp-tcp-listen-port "$CONTROLLER_PORT" "$RYU_APP")
fi

cleanup() {
  if [[ -n "${RYU_PID:-}" ]]; then
    kill "$RYU_PID" >/dev/null 2>&1 || true
    wait "$RYU_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

: >"$RYU_LOG"
"${CONTROLLER_CMD[@]}" >"$RYU_LOG" 2>&1 &
RYU_PID="$!"
sleep 2

if ! kill -0 "$RYU_PID" >/dev/null 2>&1; then
  echo "controller exited immediately"
  tail -n 120 "$RYU_LOG" || true
  exit 1
fi

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
print(f"controller did not bind port $CONTROLLER_PORT: {last_error}", file=sys.stderr)
sys.exit(1)
PY
then
  echo "controller failed to bind"
  tail -n 120 "$RYU_LOG" || true
  exit 1
fi

echo "controller is listening on port $CONTROLLER_PORT"
tail -n 40 "$RYU_LOG" || true

if [[ "$MODE" == "--hold" || "$MODE" == "hold" ]]; then
  echo "holding controller open; press Ctrl+C to stop"
  wait "$RYU_PID"
fi
