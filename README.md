# Adaptive Cloud SDN Platform - Integrated Team Delivery

This ZIP contains a completed Linux-oriented integrated development package built by merging the four uploaded team components into one project structure.

## What is included

- **Integrated orchestration API** that unifies intents, context updates, resource plans, ML recommendations, and security actions.
- **Hybrid RR + GA resource optimizer** adapted from Component 1.
- **Monitoring, Prometheus, Grafana, and ML policy integration** adapted from Component 2.
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
