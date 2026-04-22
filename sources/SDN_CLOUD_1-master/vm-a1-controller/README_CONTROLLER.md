# VM-A1 (Controller VM) Setup

This VM runs the **SDN Controller Layer** (Ryu) with the **Hybrid Load Balancer**:
- **Round Robin (RR)** for fast per-flow decisions
- **Genetic Algorithm (GA)** for periodic long-term optimization

## 1) Recommended VM specs
- 2 vCPU
- 2–4 GB RAM
- 20 GB disk

## 2) OS
Ubuntu 20.04/22.04 recommended.

## 3) Install system packages
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

## 4) Copy the project to the VM
Copy the entire `vm-a1-controller/` folder into the VM (e.g., via SCP or shared folder).

Example:
```bash
mkdir -p ~/hybrid-lb-controller
cp -r vm-a1-controller/* ~/hybrid-lb-controller/
cd ~/hybrid-lb-controller
```

## 5) Create a Python venv and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-controller.txt
```

## 6) Configure
Edit `config.controller.yaml` if needed:
- REST API port
- polling interval
- GA interval
- VIP and backend definitions

For the default Mininet topology (on VM-A2), the backend ports are:
- port 2 -> h2 (10.0.0.2)
- port 3 -> h3 (10.0.0.3)
- port 4 -> h4 (10.0.0.4)

## 7) Open firewall ports (if UFW is enabled)
OpenFlow + REST API:
```bash
sudo ufw allow 6633/tcp
sudo ufw allow 8080/tcp
```

## 8) Run the controller
```bash
chmod +x ./run_controller.sh
./run_controller.sh
```

Optional (explicit ports):
```bash
OFP_PORT=6633 REST_PORT=8080 CONFIG=./config.controller.yaml ./run_controller.sh
```

## 9) Quick checks
- Confirm the controller is listening:
```bash
sudo ss -lntp | egrep '(:6633|:8080)'
```

- Once Mininet connects from VM-A2, you should see:
`Datapath connected: dpid=1`

- REST API (after controller starts):
```bash
curl http://localhost:8080/lb/status
```
