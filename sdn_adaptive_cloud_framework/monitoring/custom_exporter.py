"""Prometheus exporter for custom SDN metrics (Module 5).

Run with::

    python -m sdn_adaptive_cloud_framework.monitoring.custom_exporter

It scrapes the controller's in-memory state via the REST API and exposes
SDN-specific metrics on :9108/metrics.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests

try:
    from prometheus_client import Gauge, start_http_server
    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover - optional dep at import time
    Gauge = None  # type: ignore[assignment]
    start_http_server = None  # type: ignore[assignment]
    _PROM_AVAILABLE = False


CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "http://127.0.0.1:8080")
EXPORTER_PORT = int(os.environ.get("PROMETHEUS_EXPORTER_PORT", "9108"))


def build_metrics():
    if not _PROM_AVAILABLE:
        raise RuntimeError("prometheus_client is not installed")
    return {
        "active_flows": Gauge("sdn_active_flows", "Number of installed flow rules"),
        "active_intents": Gauge("sdn_active_intents", "Number of registered intents"),
        "known_hosts": Gauge("sdn_known_hosts", "Hosts learned by the controller"),
        "switches": Gauge("sdn_switches", "Switches connected to the controller"),
        "context_threat": Gauge("sdn_context_threat_level", "Current threat level (0=low,1=med,2=high)"),
        "context_congestion": Gauge("sdn_context_congestion_level", "Current congestion level (0=low,1=med,2=high)"),
        "context_latency_ms": Gauge("sdn_context_latency_ms", "Latency reported via /api/context/update"),
    }


def _scrape_once(metrics) -> Optional[dict]:
    try:
        ctx = requests.get(f"{CONTROLLER_URL}/api/context/current", timeout=1.5).json()
        intents = requests.get(f"{CONTROLLER_URL}/api/intent/list", timeout=1.5).json()
        flows = requests.get(f"{CONTROLLER_URL}/api/flow/list", timeout=1.5).json()
        topo = requests.get(f"{CONTROLLER_URL}/api/network/topology", timeout=1.5).json()
        hosts = requests.get(f"{CONTROLLER_URL}/api/network/hosts", timeout=1.5).json()
    except Exception:
        return None

    level_map = {"low": 0, "medium": 1, "high": 2}
    context = ctx.get("context", {})
    metrics["active_flows"].set(len(flows.get("flows", [])))
    metrics["active_intents"].set(len(intents.get("intents", [])))
    metrics["known_hosts"].set(len(hosts.get("hosts", [])))
    metrics["switches"].set(len(topo.get("switches", [])))
    metrics["context_threat"].set(level_map.get(context.get("threat", "low"), 0))
    metrics["context_congestion"].set(level_map.get(context.get("congestion", "low"), 0))
    metrics["context_latency_ms"].set(float(context.get("latency_ms", 0.0)))
    return ctx


def main() -> None:
    if not _PROM_AVAILABLE:
        raise SystemExit("prometheus_client missing; pip install prometheus-client")
    metrics = build_metrics()
    start_http_server(EXPORTER_PORT)
    while True:
        _scrape_once(metrics)
        time.sleep(5)


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["build_metrics", "main", "CONTROLLER_URL", "EXPORTER_PORT"]
