#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

fix_perms() {
  find "$ROOT_DIR" -type f \( -name "*.sh" -o -name "manage.sh" \) -exec chmod +x {} +
  echo "[OK] Shell script permissions repaired under: $ROOT_DIR"
}

reclaim_port() {
  local port="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill $pids >/dev/null 2>&1 || true
      sleep 1
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

controller_rest_port() {
  python3 - <<'PY'
import yaml
try:
    with open('vm-a1-controller/config.controller.yaml','r',encoding='utf-8') as f:
        cfg=yaml.safe_load(f) or {}
    print(int((cfg.get('controller') or {}).get('rest_api_port',8080)))
except Exception:
    print(8080)
PY
}

ensure_venv() {
  local venv_dir="$1"
  if [[ ! -d "$venv_dir" ]]; then
    echo "[ERROR] Missing virtual environment: $venv_dir"
    echo "Run bootstrap first."
    exit 1
  fi
}

stop_by_pidfile() {
  local name="$1"
  local pidfile="$LOG_DIR/${name}.pid"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo "[OK] Stopped $name (PID $pid)"
    else
      echo "[INFO] $name was not running"
    fi
    rm -f "$pidfile"
  else
    echo "[INFO] No PID file for $name"
  fi
}

status_by_pidfile() {
  local name="$1"
  local pidfile="$LOG_DIR/${name}.pid"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[OK] $name running (PID $pid)"
      return 0
    fi
  fi
  echo "[INFO] $name not running"
  return 1
}

controller_bootstrap() {
  fix_perms
  cd "$ROOT_DIR"
  python3 -m venv .venv-controller
  # shellcheck disable=SC1091
  source .venv-controller/bin/activate
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r vm-a1-controller/requirements-controller.txt
  python - <<'PY'
import importlib
mods = ['yaml', 'ryu']
for m in mods:
    importlib.import_module(m)
print('[OK] Controller Python dependencies verified.')
PY
  echo "[OK] Controller environment ready."
}

controller_start() {
  fix_perms
  cd "$ROOT_DIR/vm-a1-controller"
  ensure_venv "$ROOT_DIR/.venv-controller"
  stop_by_pidfile controller >/dev/null 2>&1 || true
  local rest_port
  rest_port="$(controller_rest_port)"
  reclaim_port 6633
  reclaim_port "$rest_port"
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv-controller/bin/activate"
  nohup bash ./run_controller.sh > "$ROOT_DIR/logs/controller.log" 2>&1 &
  echo $! > "$ROOT_DIR/logs/controller.pid"
  sleep 3
  if kill -0 "$(cat "$ROOT_DIR/logs/controller.pid")" 2>/dev/null; then
    echo "[OK] Started controller (PID $(cat "$ROOT_DIR/logs/controller.pid"))"
    echo "[LOG] tail -f $ROOT_DIR/logs/controller.log"
  else
    echo "[ERROR] controller failed to stay running. Last log lines:"
    tail -n 40 "$ROOT_DIR/logs/controller.log" || true
    exit 1
  fi
}

controller_logs() {
  tail -n 120 "$ROOT_DIR/logs/controller.log"
}


dashboard_bootstrap() {
  fix_perms
  cd "$ROOT_DIR"
  python3 -m venv .venv-dashboard
  # shellcheck disable=SC1091
  source .venv-dashboard/bin/activate
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r dashboard/requirements-dashboard.txt
  python - <<'PY'
import importlib
mods = ['flask', 'requests', 'openstack', 'yaml']
for m in mods:
    importlib.import_module(m)
print('[OK] Dashboard Python dependencies verified.')
PY
  echo "[OK] Dashboard environment ready."
}

dashboard_start() {
  fix_perms
  cd "$ROOT_DIR/dashboard"
  ensure_venv "$ROOT_DIR/.venv-dashboard"
  stop_by_pidfile dashboard >/dev/null 2>&1 || true
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv-dashboard/bin/activate"
  export CONTROLLER_API_URL="${CONTROLLER_API_URL:-http://127.0.0.1:8080}"
  export DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
  export DASHBOARD_PORT="${DASHBOARD_PORT:-5050}"
  nohup bash ./run_dashboard.sh > "$ROOT_DIR/logs/dashboard.log" 2>&1 &
  echo $! > "$ROOT_DIR/logs/dashboard.pid"
  sleep 3
  if kill -0 "$(cat "$ROOT_DIR/logs/dashboard.pid")" 2>/dev/null; then
    echo "[OK] Started dashboard (PID $(cat "$ROOT_DIR/logs/dashboard.pid"))"
    echo "[INFO] Dashboard URL: http://$(hostname -I | awk '{print $1}'):${DASHBOARD_PORT}"
  else
    echo "[ERROR] dashboard failed to stay running. Last log lines:"
    tail -n 40 "$ROOT_DIR/logs/dashboard.log" || true
    exit 1
  fi
}

dashboard_logs() {
  tail -n 120 "$ROOT_DIR/logs/dashboard.log"
}

dataplane_bootstrap() {
  fix_perms
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y mininet openvswitch-switch iperf3 curl python3-pip python3-venv >/dev/null
    echo "[OK] Dataplane packages installed."
  else
    echo "[WARN] apt-get not found; install Mininet, Open vSwitch, and iperf3 manually."
  fi
}

dataplane_start() {
  fix_perms
  cd "$ROOT_DIR/vm-a2-dataplane"
  export CTRL_IP="${CTRL_IP:-192.168.56.10}"
  export CTRL_PORT="${CTRL_PORT:-6633}"
  export SERVERS="${SERVERS:-3}"
  echo "[INFO] Starting Mininet in foreground. Use CTRL_IP=<controller-ip> bash manage.sh dataplane start"
  bash ./run_mininet.sh
}

case "${1:-}" in
  fix-perms)
    fix_perms
    ;;
  controller)
    case "${2:-}" in
      bootstrap) controller_bootstrap ;;
      start) controller_start ;;
      stop) stop_by_pidfile controller ;;
      status) status_by_pidfile controller ;;
      logs) controller_logs ;;
      *) echo "Usage: bash manage.sh controller {bootstrap|start|stop|status|logs}"; exit 1 ;;
    esac
    ;;
  dashboard)
    case "${2:-}" in
      bootstrap) dashboard_bootstrap ;;
      start) dashboard_start ;;
      stop) stop_by_pidfile dashboard ;;
      status) status_by_pidfile dashboard ;;
      logs) dashboard_logs ;;
      *) echo "Usage: bash manage.sh dashboard {bootstrap|start|stop|status|logs}"; exit 1 ;;
    esac
    ;;
  dataplane)
    case "${2:-}" in
      bootstrap) dataplane_bootstrap ;;
      start) dataplane_start ;;
      *) echo "Usage: bash manage.sh dataplane {bootstrap|start}"; exit 1 ;;
    esac
    ;;
  *)
    cat <<USAGE
Usage:
  bash manage.sh fix-perms
  bash manage.sh controller {bootstrap|start|stop|status|logs}
  bash manage.sh dashboard {bootstrap|start|stop|status|logs}
  bash manage.sh dataplane {bootstrap|start}
USAGE
    exit 1
    ;;
esac
