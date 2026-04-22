# Hybrid SDN Load Balancer – 2 VM Deployment (Option A)

This is the **2-VM** version of the Mininet-only deployment:
- **VM-A1 = SDN Controller VM** (Ryu + Hybrid RR/GA)
- **VM-A2 = SDN Data Plane VM** (Mininet + OVS + emulated hosts + benchmarks)

## Folder mapping
- `vm-a1-controller/` → copy to VM-A1
- `vm-a2-dataplane/` → copy to VM-A2

## Recommended order
1. Configure VM networking (see `NETWORK_SETUP.md`)
2. Setup VM-A1 (controller) using `vm-a1-controller/README_CONTROLLER.md`
3. Setup VM-A2 (dataplane) using `vm-a2-dataplane/README_DATAPLANE.md`
4. Run experiments (RR-only, GA-weighted, Hybrid)

## Expected working demo
- Run the controller on VM-A1
- Start Mininet on VM-A2
- In Mininet CLI, test:
  - `h1 curl http://10.0.0.100:8000`
  - `h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 50 --duration 20 --sla-ms 200`

If traffic is working, VM-A1 logs will show flow installations and backend choices.
