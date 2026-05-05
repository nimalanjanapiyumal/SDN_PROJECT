"""Backend server inventory used by the load balancer."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from threading import RLock
from typing import Dict, Iterable, List, Optional


@dataclass
class ServerStatus:
    server_id: str
    ip: str
    cpu: float = 0.0
    memory: float = 0.0
    bandwidth: float = 0.0
    active_connections: int = 0
    max_connections: int = 100
    healthy: bool = True
    weight: float = 1.0

    def load_score(self) -> float:
        """Outline-defined formula:

        ``0.35*CPU + 0.25*Mem + 0.25*BW + 0.15*active_ratio``
        """
        active_ratio = (
            self.active_connections / self.max_connections
            if self.max_connections > 0 else 0.0
        )
        return (
            0.35 * self.cpu +
            0.25 * self.memory +
            0.25 * self.bandwidth +
            0.15 * active_ratio * 100
        )

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["load_score"] = self.load_score()
        return d


class ServerPool:
    def __init__(self, servers: Iterable[ServerStatus] = ()) -> None:
        self._lock = RLock()
        self._servers: Dict[str, ServerStatus] = {s.server_id: s for s in servers}

    def upsert(self, status: ServerStatus) -> None:
        with self._lock:
            self._servers[status.server_id] = status

    def update_metrics(self, server_id: str, **kwargs) -> Optional[ServerStatus]:
        with self._lock:
            srv = self._servers.get(server_id)
            if srv is None:
                return None
            for k, v in kwargs.items():
                if hasattr(srv, k):
                    setattr(srv, k, v)
            return srv

    def healthy_only(self) -> List[ServerStatus]:
        with self._lock:
            return [s for s in self._servers.values() if s.healthy]

    def all(self) -> List[ServerStatus]:
        with self._lock:
            return list(self._servers.values())

    def get(self, server_id: str) -> Optional[ServerStatus]:
        with self._lock:
            return self._servers.get(server_id)


__all__ = ["ServerStatus", "ServerPool"]
