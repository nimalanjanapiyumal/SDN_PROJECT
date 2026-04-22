#!/usr/bin/env bash
set -euo pipefail
sudo mn -c || true
sudo pkill -f 'adaptive_cloud_topology.py' || true
sudo pkill -f 'iperf3 -s' || true
sudo pkill -f 'iperf3 -c' || true
