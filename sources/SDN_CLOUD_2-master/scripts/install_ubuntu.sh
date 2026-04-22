#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

PYTHON_BIN="${PYTHON_BIN:-python3}"

select_python() {
  local candidate
  for candidate in "${PYTHON_BIN}" python3.11 python3.10 python3; do
    if ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi
    if "${candidate}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info < (3, 12) else 1)
PY
    then
      echo "${candidate}"
      return 0
    fi
  done
  echo "${PYTHON_BIN}"
}

PYTHON_BIN="$(select_python)"
PY_VERSION="$("${PYTHON_BIN}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

echo "Using Python interpreter: ${PYTHON_BIN} (version ${PY_VERSION})"

echo "[1/5] Installing Ubuntu packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y   build-essential   curl   docker.io   docker-compose-plugin   git   iperf3   jq   mininet   net-tools   openvswitch-switch   python3-dev   python3-pip   python3-venv

echo "[2/5] Enabling services"
sudo systemctl enable --now docker
sudo systemctl enable --now openvswitch-switch

echo "[3/5] Creating virtual environment"
if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info < (3, 12) else 1)
PY
then
  :
else
  echo "Warning: Python ${PY_VERSION} is newer than the preferred Ryu runtime. Python 3.10 or 3.11 is recommended if available."
fi
rm -rf "${VENV_DIR}"
"${PYTHON_BIN}" -m venv --system-site-packages "${VENV_DIR}"
activate_venv

echo "[4/5] Installing Python dependencies"
python -m pip install --upgrade "pip<24.1" "setuptools<70" wheel
python -m pip install -r "${PROJECT_ROOT}/requirements.txt"

echo "[5/5] Generating initial ML models"
cd "${PROJECT_ROOT}"
python ml/train_models.py --samples 1500

echo "Installation finished."
echo "Use:"
echo "  bash scripts/start_all.sh"
echo "or start components individually from scripts/."
