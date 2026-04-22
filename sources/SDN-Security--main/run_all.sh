#!/bin/bash
# run_all.sh — Start SDN Security Framework
# H D P Chathuranga — IT22902566

set -e
PROJECT="$HOME/sdn_security"
VENV="$PROJECT/venv/bin/activate"
LOGS="$PROJECT/logs"

echo "========================================"
echo "  SDN SECURITY FRAMEWORK — SLIIT CSNE"
echo "  IT22902566 — H D P Chathuranga"
echo "========================================"

# Create log directory
mkdir -p $LOGS
source $VENV

# 1. Start Open vSwitch
echo "[1/6] Starting Open vSwitch..."
sudo systemctl start openvswitch-switch
sleep 2
echo "✓ OVS running"

# 2. Start Ryu Controller (background)
echo "[2/6] Starting Ryu SDN Controller..."
cd $PROJECT
ryu-manager --observe-links --ofp-tcp-listen-port 6633 \
    controller/sdn_controller.py \
    > $LOGS/ryu.log 2>&1 &
RYU_PID=$!
echo $RYU_PID > $LOGS/ryu.pid
sleep 4
echo "✓ Ryu Controller PID=$RYU_PID (REST: http://localhost:8080)"

# 3. Start Suricata IDS
# 3. Start Suricata IDS
echo "[3/6] Starting Suricata IDS..."
sudo pkill suricata 2>/dev/null
sudo rm -f /var/run/suricata.pid
sleep 2
sudo suricata -c /etc/suricata/suricata.yaml -i any -D
sleep 3
echo "✓ Suricata IDS running"

# 4. Start Auth Module
echo "[4/6] Starting Continuous Auth Module..."
python3 $PROJECT/auth/auth_module.py \
    > $LOGS/auth.log 2>&1 &
echo $! > $LOGS/auth.pid
sleep 2
echo "✓ Auth Module on :5001"

# 5. Start CTI Module
echo "[5/6] Starting Threat Intelligence Module..."
python3 $PROJECT/threat_intel/cti_module.py \
    > $LOGS/cti.log 2>&1 &
echo $! > $LOGS/cti.pid
sleep 2
echo "✓ CTI Module on :5003"

# 6. Start Mininet Topology (foreground)
echo "[6/6] Starting Mininet Topology..."
echo "  Zones: Web(10.0.0.x) App(10.0.1.x) DB(10.0.2.x)"
echo ""
sudo python3 $PROJECT/topology/cloud_topology.py

# Cleanup on exit
echo "Stopping all services..."
kill $(cat $LOGS/ryu.pid) 2>/dev/null
kill $(cat $LOGS/auth.pid) 2>/dev/null
kill $(cat $LOGS/cti.pid) 2>/dev/null
sudo pkill suricata 2>/dev/null
echo "Done."
