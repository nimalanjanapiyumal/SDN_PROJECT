# Adaptive Cloud SDN Platform - Integrated Team Delivery

This ZIP contains a completed Linux-oriented integrated development package built by merging the four uploaded team components into one project structure.

## What is included

- **Integrated orchestration API** that unifies intents, context updates, resource plans, ML recommendations, and security actions.
- **Hybrid RR + GA resource optimizer** adapted from Component 1.
- **Component 1 operations console** for request routing, backend metrics, health/fault simulation, GA recompute, SLA tracking, and SDN flow-rule records.
- **Monitoring, Prometheus, Grafana, and ML policy integration** adapted from Component 2.
- **Component 2 runtime console/API** for telemetry ingestion, ML prediction, model training, Prometheus/Grafana readiness, mitigation latency, and automatic policy feedback.
- **Context-aware intent controller runtime** adapted from Component 3 with natural-language intent translation, DFPS priority scoring, adaptive OpenFlow-compatible rule generation, and team REST APIs.
- **Adaptive security enforcement runtime** adapted from Component 4 with continuous authentication, micro-segmentation, CTI/Suricata-style alert blocking, and OpenFlow-compatible rule records.
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

Use the top console buttons for production-style operation:

- **Run Integrated** calls `POST /api/v1/integrated/run` and automatically chains Component 2 telemetry, Component 3 intent/context adaptation, Component 1 workload allocation, and Component 4 security enforcement.
- **Start Auto / Stop** control the continuous combined system runner through `POST /api/v1/automation/start` and `POST /api/v1/automation/stop`.
- **Validate Stack** calls `GET /api/v1/platform/validate` and reports Prometheus, Grafana, Ryu, Mininet, OVS, Suricata, and runbook readiness.

Start the observability stack when Docker is available:

```bash
docker compose up -d prometheus grafana
```

Prometheus opens at `http://127.0.0.1:9090`, Grafana opens at `http://127.0.0.1:3000`, and the API exporter is available at `http://127.0.0.1:9108/metrics`.

Run the real SDN lab from Ubuntu/WSL/Linux after installing Ryu, Mininet, Open vSwitch, and iperf3:

```bash
bash scripts/run_integrated_sdn_lab.sh mixed 90
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

## Component 3 runtime functions

- `GET /api/v1/component-3/status` - intent translation, context adaptation, generated rules, metrics, and host status.
- `POST /api/v1/component-3/intents` - classify a high-level natural-language intent and generate OpenFlow-compatible rules.
- `POST /api/v1/component-3/context` - update threat, congestion, load, latency, resource, temporal, and policy context, then re-optimize active rules.
- `GET /api/v1/component-3/rules` - inspect generated and active Component 3 flow-rule records.
- `GET /api/v1/component-3/hosts` - view the simulated multi-tier cloud host inventory.
- `GET /api/v1/component-3/scenarios/{scenario_name}` - preview video, security, load, or multi-intent scenarios.
- `POST /api/v1/component-3/benchmark` - measure intent translation latency across repeated scenario submissions.

## Component 4 runtime functions

- `GET /api/v1/component-4/status` - security status for continuous auth, segmentation, CTI indicators, rules, and benchmark metrics.
- `POST /api/v1/component-4/auth/login` - create a continuous-auth session.
- `POST /api/v1/component-4/auth/verify` - verify each request, score anomalies, and quarantine high-risk sessions.
- `POST /api/v1/component-4/segmentation/enforce` - generate Zero Trust micro-segmentation ACL rules.
- `POST /api/v1/component-4/segmentation/evaluate` - evaluate a flow and quarantine lateral movement attempts.
- `POST /api/v1/component-4/cti/fetch` - ingest simulated TAXII/STIX indicators.
- `POST /api/v1/component-4/cti/alert` - process Suricata-style alerts and block matching IoCs.
- `GET /api/v1/component-4/rules` - inspect active security enforcement rule records.

## Integrated runtime functions

- `GET /api/v1/integrated/status` - combined Component 1-4 health, readiness, latest decision, and autonomous run history.
- `POST /api/v1/integrated/run` - automatic scenario run across monitoring, intent adaptation, resource allocation, and security enforcement.
- `GET /api/v1/automation/status` - autonomous system runner status including strategy, cycle count, next scenario, and latest automated run.
- `POST /api/v1/automation/start` - start continuous automation across all four components with interval, scenario strategy, and workload configuration.
- `POST /api/v1/automation/stop` - stop the continuous automation loop.
- `GET /api/v1/platform/validate` - local validation for Prometheus/Grafana files, Docker, exporter probes, Ryu, Mininet, OVS, Suricata, and WSL status.

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
