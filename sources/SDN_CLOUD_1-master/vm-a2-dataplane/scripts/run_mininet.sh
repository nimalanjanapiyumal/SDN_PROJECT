#!/usr/bin/env bash
set -euo pipefail

CTRL_IP="${1:-127.0.0.1}"
sudo python3 mininet/topo_lb.py --controller-ip "$CTRL_IP"
