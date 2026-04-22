#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
find "$ROOT_DIR" -type f \( -name "*.sh" -o -name "manage.sh" \) -exec chmod +x {} +
echo "[OK] Shell script permissions repaired under: $ROOT_DIR"
