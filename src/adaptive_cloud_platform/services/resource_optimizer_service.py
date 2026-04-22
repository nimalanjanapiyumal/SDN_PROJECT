from __future__ import annotations

from typing import Dict, Any, List

from sdn_hybrid_lb.algorithms.hybrid import HybridLoadBalancer
from sdn_hybrid_lb.utils.config import AppConfig


class ResourceOptimizerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.lb = HybridLoadBalancer(config)

    def backend_summary(self) -> List[Dict[str, Any]]:
        return [backend.as_dict() for backend in self.lb.backends]

    def update_backend_metric(self, backend_name: str, cpu: float | None = None, mem: float | None = None, latency: float | None = None) -> None:
        self.lb.update_backend_util_from_prometheus(backend_name, cpu, mem, latency)

    def recompute_weights(self) -> Dict[str, float]:
        return self.lb.force_ga()

    def build_plan(self) -> Dict[str, Any]:
        weights = self.recompute_weights()
        return {
            'source': 'optimizer',
            'plan_version': '1.0.0',
            'backend_weights': weights,
            'reason': 'hybrid rr+ga recompute',
        }
