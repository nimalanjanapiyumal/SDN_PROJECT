# Ubuntu VM Deployment Guide

## Recommended VM profile

- 8 vCPU
- 16 GB RAM
- 40+ GB free disk for experiments
- Ubuntu 22.04 LTS is recommended
- Ubuntu Server or Ubuntu Desktop
- nested virtualization is **not** required

## Prerequisites

Install the project into a normal user account and run Mininet commands through `sudo`.

## Step 1 - unpack the project

```bash
unzip sdn_adaptive_cloud_bundle.zip
cd sdn_adaptive_cloud
```

## Step 2 - install dependencies

```bash
bash scripts/install_ubuntu.sh
```

This script:

- installs Mininet, Open vSwitch, Docker, and Python build tooling,
- creates `.venv`,
- pins Python packaging tools for Ryu compatibility,
- installs Python dependencies,
- generates the first trained models.

## Step 3 - start observability

```bash
bash scripts/start_observability.sh
```

Access:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- default Grafana credentials: `admin` / `admin`

## Step 4 - start the controller

```bash
bash scripts/start_controller.sh
```

For foreground mode:

```bash
bash scripts/start_controller.sh --foreground
```

## Step 5 - start the ML policy agent

```bash
bash scripts/start_policy_agent.sh
```

For foreground mode:

```bash
bash scripts/start_policy_agent.sh --foreground
```

## Step 6 - run the topology

```bash
bash scripts/run_topology.sh --foreground --scenario mixed --cli
```

## Common URLs

- Ryu controller metrics: `http://127.0.0.1:9101/metrics`
- ML policy metrics: `http://127.0.0.1:9102/metrics`
- Controller API: `http://127.0.0.1:8080/api/v1/state`

## Background mode

To start the full stack in one command:

```bash
bash scripts/start_all.sh
```

Logs are stored in `logs/`.

PID files are stored in `run/`.

## Shutdown

```bash
bash scripts/stop_all.sh
```

## Typical demo sequence

### Normal traffic
```bash
bash scripts/run_topology.sh --foreground --scenario normal
```

### Congestion
```bash
bash scripts/run_topology.sh --foreground --scenario congestion
```

### DDoS-like flood
```bash
bash scripts/run_topology.sh --foreground --scenario ddos
```

### Port scan
```bash
bash scripts/run_topology.sh --foreground --scenario port_scan
```

## Troubleshooting

### `ModuleNotFoundError: mininet`
Re-run the install script. It creates the venv with `--system-site-packages`, which allows the virtual environment to use the Ubuntu-provided Mininet package.

### `ryu-manager` installation failure
The install script pins `pip` and `setuptools` inside the virtual environment before installing `ryu`. Use the provided script instead of a raw `pip install -r requirements.txt` in a brand-new environment.

### Prometheus does not show controller metrics
Confirm the controller is running and check:

```bash
curl -s http://127.0.0.1:9101/metrics | head
```

### Grafana dashboard is empty
Confirm Prometheus is up and the datasource is provisioned:

```bash
curl -s http://127.0.0.1:9090/-/healthy
```

### Mininet cleanup required
```bash
bash scripts/clean_mininet.sh
```

## Optional baseline experiment

To compare reactive vs adaptive behavior:

1. do **not** start the policy agent,
2. run the traffic scenarios and record metrics,
3. start the policy agent,
4. re-run the same scenarios,
5. compare the metrics in Grafana or Prometheus.
