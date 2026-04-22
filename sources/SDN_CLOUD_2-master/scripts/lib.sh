#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

activate_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Virtual environment not found at ${VENV_DIR}. Run bash scripts/install_ubuntu.sh first."
    exit 1
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
}

ensure_dirs() {
  mkdir -p "${PROJECT_ROOT}/logs" "${PROJECT_ROOT}/run"
}

compose() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    docker compose -f "${PROJECT_ROOT}/docker-compose.yml" "$@"
  else
    sudo docker compose -f "${PROJECT_ROOT}/docker-compose.yml" "$@"
  fi
}

wait_for_url() {
  local url="$1"
  local attempts="${2:-20}"
  local sleep_seconds="${3:-1}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  return 1
}

stop_pidfile() {
  local pidfile="$1"
  if [[ -f "${pidfile}" ]]; then
    local pid
    pid="$(cat "${pidfile}")"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || sudo kill "${pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${pidfile}"
  fi
}
