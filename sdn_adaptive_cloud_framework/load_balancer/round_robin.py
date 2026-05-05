"""Round-Robin server selector (Module 4 - immediate decision path)."""
from __future__ import annotations

from itertools import cycle
from threading import Lock
from typing import Iterable, List, Optional

from .server_monitor import ServerStatus


class RoundRobin:
    def __init__(self, servers: Iterable[ServerStatus]) -> None:
        self._servers: List[ServerStatus] = list(servers)
        self._cycle = cycle(self._servers) if self._servers else None
        self._lock = Lock()

    def update_pool(self, servers: Iterable[ServerStatus]) -> None:
        with self._lock:
            self._servers = list(servers)
            self._cycle = cycle(self._servers) if self._servers else None

    def select(self) -> Optional[ServerStatus]:
        with self._lock:
            if not self._servers or self._cycle is None:
                return None
            # Skip unhealthy servers; if all are unhealthy, return None.
            for _ in range(len(self._servers)):
                candidate = next(self._cycle)
                if candidate.healthy:
                    return candidate
            return None


__all__ = ["RoundRobin"]
