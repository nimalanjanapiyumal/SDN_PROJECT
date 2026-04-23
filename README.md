# Adaptive Cloud SDN Platform - Integrated Team Delivery

This ZIP contains a completed Linux-oriented integrated development package built by merging the four uploaded team components into one project structure.

## What is included

- **Integrated orchestration API** that unifies intents, context updates, resource plans, ML recommendations, and security actions.
- **Hybrid RR + GA resource optimizer** adapted from Component 1.
- **Component 1 operations console** for request routing, backend metrics, health/fault simulation, GA recompute, SLA tracking, and SDN flow-rule records.
- **Monitoring, Prometheus, Grafana, and ML policy integration** adapted from Component 2.
- **Component 2 runtime console/API** for telemetry ingestion, ML prediction, model training, Prometheus/Grafana readiness, mitigation latency, and automatic policy feedback.
- **Intent-based controller compatibility layer** aligned with Component 3 REST paths.
- **Continuous authentication, micro-segmentation, and CTI integration services** adapted from Component 4.
- **Linux deployment assets**: `docker-compose.yml`, `scripts/*.sh`, `deploy/systemd/*.service`, and a release packaging script.
- **Preserved original source drops** under `sources/` for traceability.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn adaptive_cloud_platform.app:app --app-dir src --host 0.0.0.0 --port 8080
```

Then in another shell:

```bash
curl -s http://127.0.0.1:8080/healthz
curl -s http://127.0.0.1:8080/api/v1/state | jq
```

Open the integrated frontend at:

```text
http://127.0.0.1:8080/
```

## Component 1 runtime functions

- `GET /api/v1/component-1/status` - full Component 1 runtime status, SLA, flow rules, events, weights, and backend pool.
- `GET /api/v1/component-1/platform` - reports whether local Ryu, Mininet, and OpenStack tools are available.
- `POST /api/v1/component-1/route` - route a client request through RR/SWRR and create a simulated SDN flow rule.
- `POST /api/v1/component-1/backends/{backend_name}/metrics` - update backend CPU, memory, bandwidth, latency, throughput, and active connection signals.
- `POST /api/v1/component-1/backends/{backend_name}/health` - enable or fault a backend for fault-tolerance testing.
- `POST /api/v1/component-1/workload/simulate` - run a repeatable load-balancing simulation and optionally inject a backend fault.
- `POST /api/v1/resource-plans/recompute` - run the Genetic Algorithm and publish optimized backend weights.

## Component 2 runtime functions

- `GET /api/v1/component-2/status` - monitoring, prediction, model, and evaluation status.
- `GET /api/v1/component-2/platform` - Prometheus/Grafana/tooling readiness.
- `POST /api/v1/component-2/telemetry` - ingest live telemetry, run ML prediction, and trigger automatic allocation feedback.
- `GET /api/v1/component-2/scenarios/{scenario_name}` - preview normal, congestion, ddos, or port_scan telemetry scenarios.
- `POST /api/v1/component-2/models/train` - train the anomaly classifier and SLA-risk regressor.

## Main directories

- `src/adaptive_cloud_platform/` - new integrated services and API
- `src/adaptive_cloud_platform/frontend/` - no-build frontend dashboard, structured by Components 1-4
- `src/sdn_hybrid_lb/` - reusable hybrid optimization code
- `src/ml/` - monitoring/ML helpers from the monitoring component
- `src/security_modules/` - security services from the security component
- `src/topology/` - Mininet topology scripts
- `monitoring/` - Prometheus and Grafana provisioning
- `deploy/systemd/` - Linux service units
- `sources/` - original uploaded component code snapshots

## Integration idea

The integrated runtime keeps **one policy spine**: security actions override manual intents, manual intents override ML recommendations, and ML recommendations override optimizer plans. The final action is exposed through a single state API and a compatibility layer so the original component endpoints can still be used.
