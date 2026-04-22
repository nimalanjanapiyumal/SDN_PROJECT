# Linux Deployment Guide

## Option A - direct host deployment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn adaptive_cloud_platform.app:app --app-dir src --host 0.0.0.0 --port 8080
```

## Option B - Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

## Option C - systemd

```bash
sudo cp deploy/systemd/adaptive-cloud-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now adaptive-cloud-api.service
```

## Optional lab components

- `src/topology/adaptive_cloud_topology.py` for a 4-switch lab.
- `src/topology/cloud_three_tier_topology.py` for a 6-switch, 15-host three-tier cloud topology.

## Notes

The integrated API is runnable without Ryu or Mininet. Ryu/Mininet are optional lab dependencies for live SDN demonstrations.
