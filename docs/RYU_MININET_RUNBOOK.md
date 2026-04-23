# Ryu and Mininet Runbook

This project runs the combined model in FastAPI on Windows, Docker, or Linux. Real OpenFlow enforcement needs a Linux SDN lab because Mininet and Open vSwitch are Linux-native.

## Runtime Topology

- FastAPI integrated policy plane: `http://127.0.0.1:8080`
- Prometheus metrics exporter: `http://127.0.0.1:9108/metrics`
- Ryu bridge controller: `src/adaptive_cloud_platform/sdn/ryu_integrated_app.py`
- Mininet topology: `src/topology/adaptive_cloud_topology.py`

## Start the API

```bash
python -m uvicorn adaptive_cloud_platform.app:app --app-dir src --host 0.0.0.0 --port 8080
```

## Start Observability

```bash
docker compose up -d prometheus grafana
```

Grafana opens at `http://127.0.0.1:3000` and Prometheus opens at `http://127.0.0.1:9090`.

## Start Ryu and Mininet

Run this from Ubuntu/WSL/Linux with Ryu, Mininet, Open vSwitch, and iperf3 installed:

```bash
bash scripts/run_integrated_sdn_lab.sh mixed 90
```

The script starts Ryu, connects Mininet to `127.0.0.1:6653`, launches a traffic scenario, and syncs Component 4 block/quarantine rules from the FastAPI backend into OpenFlow drop rules.

## Validation

Use the platform validator:

```bash
curl -s http://127.0.0.1:8080/api/v1/platform/validate | jq
```

On Windows, the validator is expected to report the FastAPI and configuration files as ready while marking Mininet/Ryu/Suricata binaries unavailable unless they are installed in the active shell. On Ubuntu/WSL/Linux, `ryu-manager`, `mn`, `ovs-ofctl`, and `iperf3` should resolve before running the real dataplane lab.
