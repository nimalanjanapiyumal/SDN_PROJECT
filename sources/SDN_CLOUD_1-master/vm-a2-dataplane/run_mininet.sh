#!/usr/bin/env bash
set -euo pipefail

# Hybrid SDN Load Balancer - Data Plane VM launcher
#
# Env vars (optional):
#   CTRL_IP    Controller VM IP on the shared network (default 192.168.56.10)
#   CTRL_PORT  OpenFlow port (default 6633)
#   SERVERS    Number of backends (1-4, default 3)
#
# Example:
#   CTRL_IP=192.168.56.10 CTRL_PORT=6633 SERVERS=3 ./run_mininet.sh

CTRL_IP="${CTRL_IP:-192.168.56.10}"
CTRL_PORT="${CTRL_PORT:-6633}"
SERVERS="${SERVERS:-3}"

sudo python3 mininet/topo_lb.py \
  --controller-ip "$CTRL_IP" \
  --controller-port "$CTRL_PORT" \
  --servers "$SERVERS"
