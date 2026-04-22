#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-controller}"
if [[ "$MODE" == "controller" ]]; then
  echo '[Diag] Listening ports:'
  ss -lntp | grep -E ':(6633|8080) ' || true
elif [[ "$MODE" == "dataplane" ]]; then
  IP="${CTRL_IP:-127.0.0.1}"; PORT="${CTRL_PORT:-6633}"
  echo "[Diag] Controller target ${IP}:${PORT}"
  python3 - <<PY
import socket
ip='${IP}'; port=int('${PORT}')
try:
    s=socket.create_connection((ip,port),timeout=2); s.close(); print('reachable')
except Exception as e:
    print(f'unreachable: {e}')
PY
  ovs-vsctl show || true
  ovs-ofctl -O OpenFlow13 show s1 || true
  ovs-ofctl -O OpenFlow13 dump-flows s1 || true
fi
