# VM-A2 (Data Plane VM) Setup

This VM runs:
- **Mininet** topology (OVS switch + emulated hosts)
- **Backends** (Python HTTP servers in Mininet hosts)
- **Traffic generation / benchmarking** (HTTP benchmark and/or iperf3)

## 1) Recommended VM specs
- 2 vCPU
- 4 GB RAM (Mininet + OVS + CLI runs smoother)
- 20 GB disk

## 2) OS
Ubuntu 20.04/22.04 recommended.

## 3) Install packages
```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch iperf3 python3
```

(Optional sanity test)
```bash
sudo mn --test pingall
```

## 4) Copy the project to the VM
Copy the entire `vm-a2-dataplane/` folder into the VM (e.g., via SCP or shared folder).

Example:
```bash
mkdir -p ~/hybrid-lb-dataplane
cp -r vm-a2-dataplane/* ~/hybrid-lb-dataplane/
cd ~/hybrid-lb-dataplane
```

## 5) Run Mininet and connect to the remote controller (VM-A1)
```bash
chmod +x ./run_mininet.sh
CTRL_IP=192.168.56.10 CTRL_PORT=6633 SERVERS=3 ./run_mininet.sh
```

You should see Mininet CLI.

### Quick manual tests in Mininet
```bash
mininet> pingall
mininet> h1 curl http://10.0.0.100:8000
```

### Run the HTTP benchmark from inside Mininet
```bash
mininet> h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 50 --duration 20 --sla-ms 200
```

### (Optional) iperf3 test
Start servers on backends:
```bash
mininet> h2 iperf3 -s -D
mininet> h3 iperf3 -s -D
mininet> h4 iperf3 -s -D
```
Then run a client flow (note: iperf3 targets a single host; HTTP testing is better for VIP-based LB):
```bash
mininet> h1 iperf3 -c 10.0.0.100 -t 10
```

## 6) Cleanup tips
If Mininet gets stuck:
```bash
sudo mn -c
sudo systemctl restart openvswitch-switch
```
