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

## OpenStack Controls

For a Linux operator host, the GUI now maps to the same commands below:

```bash
bash scripts/control_openstack.sh deploy auto
bash scripts/control_openstack.sh start auto
bash scripts/control_openstack.sh stop auto
bash scripts/control_openstack.sh inventory auto
```

The current runtime path targets a single-node MicroStack deployment. If `microstack` is not installed but `snap` is available, the deploy step will try to install MicroStack first.

## Start Ryu and Mininet

Run this from Ubuntu/WSL/Linux with Ryu, Mininet, Open vSwitch, and iperf3 installed:

```bash
bash scripts/run_integrated_sdn_lab.sh mixed 90
```

The script starts Ryu, connects Mininet to `127.0.0.1:6653`, launches a traffic scenario, and syncs Component 4 block/quarantine rules from the FastAPI backend into OpenFlow drop rules.

## Debug Ryu Startup on VMA1

Before launching the full lab, verify the controller in isolation:

```bash
bash scripts/debug_ryu_controller.sh
```

This performs the following checks in order:

1. Confirms `python3`, `ryu-manager` or the Python `ryu` module, `mn`, and `ovs-vsctl`
2. Compiles `src/adaptive_cloud_platform/sdn/ryu_integrated_app.py`
3. Imports the controller app directly
4. Warns if the FastAPI API at `ADAPTIVE_API_URL` is unavailable
5. Checks whether port `6653` is already in use
6. Starts only the Ryu controller and waits for the OpenFlow port to bind
7. Prints the recent Ryu log if startup fails

The controller wrapper also forces:

```bash
export EVENTLET_NO_GREENDNS=yes
```

and applies Python 3.10 compatibility aliases for older `eventlet` / `dnspython`
combinations that still reference `collections.MutableMapping`.

To keep the controller running for manual inspection:

```bash
bash scripts/debug_ryu_controller.sh --hold
```

If that succeeds, launch the full lab:

```bash
bash scripts/run_integrated_sdn_lab.sh mixed 90 headless basic
```

Useful follow-up checks on Linux:

```bash
ss -ltnp | grep 6653
tail -n 120 logs/ryu_integrated.log
curl -s http://127.0.0.1:8080/healthz
sudo ovs-vsctl show
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

## Validation

Use the platform validator:

```bash
curl -s http://127.0.0.1:8080/api/v1/platform/validate | jq
```

On Windows, the validator is expected to report the FastAPI and configuration files as ready while marking Mininet/Ryu/Suricata binaries unavailable unless they are installed in the active shell. On Ubuntu/WSL/Linux, `ryu-manager`, `mn`, `ovs-ofctl`, and `iperf3` should resolve before running the real dataplane lab.
