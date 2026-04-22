#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

ensure_dirs
cd "${PROJECT_ROOT}"

echo "Starting Prometheus and Grafana"
compose up -d prometheus grafana

if wait_for_url "http://127.0.0.1:9090/-/healthy" 40 1; then
  echo "Prometheus is up at http://127.0.0.1:9090"
else
  echo "Prometheus health check failed"
fi

if wait_for_url "http://127.0.0.1:3000/api/health" 40 1; then
  echo "Grafana is up at http://127.0.0.1:3000"
else
  echo "Grafana health check failed"
fi
