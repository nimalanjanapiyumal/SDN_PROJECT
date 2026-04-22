from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
import itertools

from sdn_hybrid_lb.utils.models import BackendServer


class RoundRobinSelector:
    """Simple Round Robin over eligible servers."""

    def __init__(self) -> None:
        self._idx = 0

    def choose(self, servers: Sequence[BackendServer]) -> Optional[BackendServer]:
        if not servers:
            return None
        srv = servers[self._idx % len(servers)]
        self._idx = (self._idx + 1) % (10**9)
        return srv


@dataclass
class _SWRRState:
    current_weight: float = 0.0
    effective_weight: float = 1.0


class SmoothWeightedRoundRobin:
    """Smooth Weighted Round Robin (SWRR).

    Deterministic WRR that avoids burstiness. Used by Nginx, LVS, etc.

    Algorithm:
      - each server has effective_weight (>=0) and current_weight
      - on each selection:
          current_weight += effective_weight
          choose server with max current_weight
          chosen.current_weight -= total_effective_weight
    """

    def __init__(self) -> None:
        self._state: Dict[str, _SWRRState] = {}

    def set_weights(self, servers: Sequence[BackendServer], weights: Dict[str, float]) -> None:
        # Ensure state exists
        for s in servers:
            st = self._state.setdefault(s.name, _SWRRState())
            w = float(weights.get(s.name, 1.0))
            if w < 0:
                w = 0.0
            st.effective_weight = w

    def choose(self, servers: Sequence[BackendServer]) -> Optional[BackendServer]:
        if not servers:
            return None

        # Ensure all have state
        total = 0.0
        for s in servers:
            st = self._state.setdefault(s.name, _SWRRState())
            total += st.effective_weight

        if total <= 0.0:
            # fallback: treat all equal
            for s in servers:
                self._state.setdefault(s.name, _SWRRState()).effective_weight = 1.0
            total = float(len(servers))

        best: Optional[BackendServer] = None
        best_weight = None

        for s in servers:
            st = self._state[s.name]
            st.current_weight += st.effective_weight
            if best is None or (best_weight is None) or (st.current_weight > best_weight):
                best = s
                best_weight = st.current_weight

        assert best is not None
        self._state[best.name].current_weight -= total
        return best
