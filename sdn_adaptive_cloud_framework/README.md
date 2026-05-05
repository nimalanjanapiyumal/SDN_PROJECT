# SDN-Based Adaptive Cloud Network Management Framework

Modular SDN platform implementing the development outline:

* **Module 1** Intelligent SDN controller (Ryu app + REST surface)
* **Module 2** Intent processing engine
* **Module 3** Dynamic Flow Priority Scheduling (DFPS)
* **Module 4** Hybrid load balancer (Round Robin + Genetic Algorithm)
* **Module 5** Monitoring (Prometheus exporter + Grafana dashboard)
* **Module 6** ML prediction (heuristic baseline + sklearn pipeline)
* **Module 7** Adaptive security (continuous auth, micro-segmentation, CTI, Suricata)

## Layout

```
sdn_adaptive_cloud_framework/
  controller/       # Ryu app, intent processor, DFPS, flow manager, host/topology
  api/              # FastAPI app, route modules, Pydantic schemas
  load_balancer/    # RR + GA + hybrid scheduler + server pool
  monitoring/       # Prometheus exporter + Grafana dashboards + prom config
  ml_module/        # train_model, predict, dataset/
  security/         # auth, micro-segmentation, threat-intel, suricata, quarantine
  topology/         # Mininet topology + evaluation scenarios
  tests/            # pytest tests for controller, LB, security, ML, API
  docs/             # architecture.md, api_spec.md, evaluation_plan.md
```

## Quick start (Ubuntu / Mininet host)

```bash
# 1. install python deps (the repo's existing requirements.txt covers this)
pip install -r ../requirements.txt

# 2. run the REST API
uvicorn sdn_adaptive_cloud_framework.api.app:app --host 0.0.0.0 --port 8080

# 3. run the Ryu controller (separate shell)
ryu-manager --observe-links sdn_adaptive_cloud_framework.controller.ryu_controller

# 4. run Mininet topology (separate shell, root)
sudo python3 -m sdn_adaptive_cloud_framework.topology.mininet_topology
```

Submit an intent:

```bash
curl -s -X POST http://127.0.0.1:8080/api/intent/submit \
  -H 'content-type: application/json' \
  -d '{"intent_type":"security","action":"block","src_ip":"10.0.0.5","dst_ip":"10.0.0.10","priority":100}'
```

Check learned hosts and topology:

```bash
curl -s http://127.0.0.1:8080/api/network/hosts
curl -s http://127.0.0.1:8080/api/network/topology
```

## Tests

```bash
pytest sdn_adaptive_cloud_framework -q
```

The test suite verifies the intent processor against the example payloads in
the outline, plus DFPS ranking, load-balancer fitness, security helpers, the
ML heuristic, and every REST endpoint.

## Notes on the existing `src/` package

The legacy `src/adaptive_cloud_platform/` package is left untouched so its
running deployments remain functional. This new `sdn_adaptive_cloud_framework/`
package is the redesign requested for the development outline; modules from
the legacy package can be ported one at a time as they are needed.
