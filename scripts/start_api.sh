#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
uvicorn adaptive_cloud_platform.app:app --app-dir src --host 0.0.0.0 --port 8080
