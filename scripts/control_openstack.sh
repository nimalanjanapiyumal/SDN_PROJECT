#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
MODE="${2:-auto}"

run_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  else
    sudo -n "$@"
  fi
}

ensure_microstack() {
  if command -v microstack >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v snap >/dev/null 2>&1; then
    echo "snap is required to install MicroStack automatically" >&2
    exit 1
  fi
  echo "Installing MicroStack via snap"
  run_root snap install microstack --classic
}

case "$ACTION" in
  deploy)
    case "$MODE" in
      auto|microstack)
        ensure_microstack
        echo "Initializing MicroStack"
        run_root microstack init --auto --control
        ;;
      *)
        echo "Unsupported OpenStack deployment mode: $MODE" >&2
        exit 1
        ;;
    esac
    ;;
  start)
    case "$MODE" in
      auto|microstack)
        command -v microstack >/dev/null 2>&1 || { echo "MicroStack is not installed" >&2; exit 1; }
        echo "Starting MicroStack"
        run_root microstack start
        ;;
      *)
        echo "Unsupported OpenStack start mode: $MODE" >&2
        exit 1
        ;;
    esac
    ;;
  stop)
    case "$MODE" in
      auto|microstack)
        command -v microstack >/dev/null 2>&1 || { echo "MicroStack is not installed" >&2; exit 1; }
        echo "Stopping MicroStack"
        run_root microstack stop
        ;;
      *)
        echo "Unsupported OpenStack stop mode: $MODE" >&2
        exit 1
        ;;
    esac
    ;;
  status)
    if command -v microstack >/dev/null 2>&1; then
      microstack status || true
    else
      echo "MicroStack not installed"
    fi
    if command -v openstack >/dev/null 2>&1; then
      openstack service list || true
    else
      echo "OpenStack CLI not installed"
    fi
    ;;
  inventory)
    command -v openstack >/dev/null 2>&1 || { echo "OpenStack CLI is not installed" >&2; exit 1; }
    echo "Servers"
    openstack server list || true
    echo
    echo "Networks"
    openstack network list || true
    ;;
  *)
    echo "Usage: $0 <deploy|start|stop|status|inventory> [auto|microstack]" >&2
    exit 1
    ;;
esac
