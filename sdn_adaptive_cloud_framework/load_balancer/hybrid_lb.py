"""Hybrid RR + GA load balancer (Module 4).

* RR drives every individual request decision (fast).
* GA periodically re-orders the RR pool so RR cycles through the
  best-performing backends first.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .genetic_algorithm import GAConfig, optimise_server_order
from .round_robin import RoundRobin
from .server_monitor import ServerPool, ServerStatus


class HybridLoadBalancer:
    def __init__(
        self,
        pool: ServerPool,
        ga_interval_seconds: float = 30.0,
        ga_config: Optional[GAConfig] = None,
    ) -> None:
        self._pool = pool
        self._rr = RoundRobin(pool.healthy_only())
        self._ga_interval = ga_interval_seconds
        self._ga_config = ga_config or GAConfig()
        self._last_ga_run = 0.0
        self._last_order: List[ServerStatus] = []

    def select(self, force_ga: bool = False) -> Optional[Dict[str, Any]]:
        self._maybe_run_ga(force=force_ga)
        chosen = self._rr.select()
        if chosen is None:
            return None
        return {
            "selected_server": chosen.server_id,
            "next_hop_ip": chosen.ip,
            "load_score": chosen.load_score(),
            "reason": "Lowest combined load score" if chosen == self._head() else "Round-robin rotation",
        }

    def _head(self) -> Optional[ServerStatus]:
        return self._last_order[0] if self._last_order else None

    def _maybe_run_ga(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_ga_run < self._ga_interval:
            return
        healthy = self._pool.healthy_only()
        if not healthy:
            self._rr.update_pool([])
            self._last_order = []
            return
        ordered = optimise_server_order(healthy, self._ga_config)
        self._rr.update_pool(ordered)
        self._last_order = ordered
        self._last_ga_run = now


__all__ = ["HybridLoadBalancer"]
