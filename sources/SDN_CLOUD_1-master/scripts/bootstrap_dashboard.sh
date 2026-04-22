#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
python3 -m venv .venv-dashboard
source .venv-dashboard/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r dashboard/requirements-dashboard.txt
chmod +x dashboard/run_dashboard.sh

echo "[OK] Dashboard environment ready."
echo "Run with: source .venv-dashboard/bin/activate && export CONTROLLER_API_URL=http://<controller-ip>:8080 && bash dashboard/run_dashboard.sh"
