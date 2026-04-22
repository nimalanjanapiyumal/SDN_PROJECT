from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from sdn_hybrid_lb.monitoring.base import MetricsProvider
from sdn_hybrid_lb.utils.models import BackendServer


@dataclass
class PrometheusConfig:
    base_url: str
    timeout_sec: float
    promql: Dict[str, str]
    instances: Dict[str, str]  # backend_name -> instance label


class PrometheusProvider(MetricsProvider):
    """Pull CPU/memory metrics from Prometheus (optional).

    You must provide mapping backend_name -> instance label (e.g., "10.0.0.2:9100").

    PromQL templates may reference `{instance}`.
    """

    def __init__(self, cfg: PrometheusConfig) -> None:
        self.cfg = cfg
        self.base = cfg.base_url.rstrip("/")

    def update(self, backends: Sequence[BackendServer]) -> None:
        for b in backends:
            instance = self.cfg.instances.get(b.name)
            if not instance:
                continue

            cpu_q = self.cfg.promql.get("cpu_util")
            mem_q = self.cfg.promql.get("mem_util")

            cpu = self._query_scalar(cpu_q.format(instance=instance)) if cpu_q else None
            mem = self._query_scalar(mem_q.format(instance=instance)) if mem_q else None

            if cpu is not None:
                b.metrics.cpu_util = float(max(0.0, min(1.0, cpu)))
            if mem is not None:
                b.metrics.mem_util = float(max(0.0, min(1.0, mem)))

    def _query_scalar(self, promql: str) -> Optional[float]:
        url = f"{self.base}/api/v1/query?{urllib.parse.urlencode({'query': promql})}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        try:
            if payload.get("status") != "success":
                return None
            data = payload.get("data") or {}
            result = data.get("result") or []
            if not result:
                return None
            value = result[0].get("value")
            # value: [timestamp, "number"]
            if not value or len(value) < 2:
                return None
            return float(value[1])
        except Exception:
            return None
