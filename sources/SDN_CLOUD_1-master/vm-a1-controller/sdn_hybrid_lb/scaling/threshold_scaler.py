from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, Optional
import time

from sdn_hybrid_lb.utils.models import BackendServer


class ScalerBackend(Protocol):
    def scale_out(self, count: int = 1) -> None:
        ...

    def scale_in(self, count: int = 1) -> None:
        ...


@dataclass
class Thresholds:
    cpu_high: float = 0.80
    cpu_low: float = 0.20
    mem_high: float = 0.80
    mem_low: float = 0.20


class ThresholdScaler:
    """Optional: threshold-based scaling trigger.

    This is a *skeleton* that can be wired to OpenStack Heat/Nova or Kubernetes.
    It is intentionally conservative: it triggers only when enough metrics exist.
    """

    def __init__(
        self,
        backend: ScalerBackend,
        thresholds: Thresholds = Thresholds(),
        cooldown_sec: int = 60,
    ) -> None:
        self.backend = backend
        self.th = thresholds
        self.cooldown_sec = cooldown_sec
        self._last_action = 0.0

    def tick(self, servers: Sequence[BackendServer]) -> Optional[str]:
        now = time.time()
        if (now - self._last_action) < self.cooldown_sec:
            return None

        cpu_vals = [s.metrics.cpu_util for s in servers if s.metrics.cpu_util is not None]
        mem_vals = [s.metrics.mem_util for s in servers if s.metrics.mem_util is not None]
        if not cpu_vals and not mem_vals:
            return None

        cpu_avg = sum(cpu_vals) / len(cpu_vals) if cpu_vals else None
        mem_avg = sum(mem_vals) / len(mem_vals) if mem_vals else None

        # Scale out
        if (cpu_avg is not None and cpu_avg >= self.th.cpu_high) or (mem_avg is not None and mem_avg >= self.th.mem_high):
            self.backend.scale_out(count=1)
            self._last_action = now
            return "scale_out"

        # Scale in
        if (cpu_avg is not None and cpu_avg <= self.th.cpu_low) and (mem_avg is not None and mem_avg <= self.th.mem_low):
            self.backend.scale_in(count=1)
            self._last_action = now
            return "scale_in"

        return None
