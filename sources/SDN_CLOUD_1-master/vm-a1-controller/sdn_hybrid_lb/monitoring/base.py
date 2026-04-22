from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from sdn_hybrid_lb.utils.models import BackendServer


class MetricsProvider(ABC):
    @abstractmethod
    def update(self, backends: Sequence[BackendServer]) -> None:
        """Update metrics for the given backends in-place."""
        raise NotImplementedError
