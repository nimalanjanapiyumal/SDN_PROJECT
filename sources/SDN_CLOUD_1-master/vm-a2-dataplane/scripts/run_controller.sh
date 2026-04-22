#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${SDN_HYBRID_LB_CONFIG:-./config.example.yaml}"
PORT="$(python3 - <<'PY'
import yaml, os
p=os.environ.get("SDN_HYBRID_LB_CONFIG","./config.example.yaml")
with open(p,"r",encoding="utf-8") as f:
    d=yaml.safe_load(f) or {}
print(int((d.get("controller") or {}).get("rest_api_port",8080)))
PY
)"

export SDN_HYBRID_LB_CONFIG="$CONFIG_PATH"

echo "Using config: $SDN_HYBRID_LB_CONFIG"
echo "Starting Ryu app on wsapi port: $PORT"

# ryu-manager supports --wsapi-port in most installations.
# If your version does not, remove the flag and use the default.
ryu-manager --wsapi-port "$PORT" sdn_hybrid_lb/controller/ryu_app.py
