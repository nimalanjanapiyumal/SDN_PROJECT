#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-./config.controller.yaml}"
OFP_PORT="${OFP_PORT:-6633}"

REST_PORT_DEFAULT="$(CONFIG="$CONFIG" python3 - <<'PY'
import os, yaml
cfg_path = os.environ.get('CONFIG', './config.controller.yaml')
try:
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    print(int((cfg.get('controller') or {}).get('rest_api_port', 8080)))
except Exception:
    print(8080)
PY
)"
REST_PORT="${REST_PORT:-$REST_PORT_DEFAULT}"

export SDN_HYBRID_LB_CONFIG="$CONFIG"
export EVENTLET_NO_GREENDNS="${EVENTLET_NO_GREENDNS:-yes}"

echo "[Controller] Using config: $SDN_HYBRID_LB_CONFIG"
echo "[Controller] OpenFlow listen port: $OFP_PORT"
echo "[Controller] REST API port: $REST_PORT"

python3 ./launch_ryu_compat.py \
  --ofp-tcp-listen-port "$OFP_PORT" \
  --wsapi-port "$REST_PORT" \
  sdn_hybrid_lb/controller/ryu_app.py
