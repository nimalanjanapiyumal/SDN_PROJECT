from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
import time


@dataclass(frozen=True)
class Capacity:
    cpu_cores: float = 1.0
    mem_gb: float = 1.0
    bw_mbps: float = 1000.0


@dataclass
class Metrics:
    # Normalized utilizations: 0.0 .. 1.0 (best effort; may be derived)
    cpu_util: Optional[float] = None
    mem_util: Optional[float] = None
    bw_util: Optional[float] = None

    # Traffic/session indicators
    active_connections: int = 0
    latency_ms: Optional[float] = None
    throughput_mbps: Optional[float] = None

    updated_at: float = field(default_factory=lambda: time.time())

    def as_dict(self) -> Dict:
        return {
            "cpu_util": self.cpu_util,
            "mem_util": self.mem_util,
            "bw_util": self.bw_util,
            "active_connections": self.active_connections,
            "latency_ms": self.latency_ms,
            "throughput_mbps": self.throughput_mbps,
            "updated_at": self.updated_at,
        }


@dataclass
class BackendServer:
    name: str
    ip: str
    mac: str
    dpid: int
    port: int
    capacity: Capacity = field(default_factory=Capacity)

    # Runtime state
    healthy: bool = True
    weight: float = 1.0
    current_weight: float = 0.0  # used by smooth weighted RR
    metrics: Metrics = field(default_factory=Metrics)

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "ip": self.ip,
            "mac": self.mac,
            "dpid": self.dpid,
            "port": self.port,
            "capacity": asdict(self.capacity),
            "healthy": self.healthy,
            "weight": self.weight,
            "current_weight": self.current_weight,
            "metrics": self.metrics.as_dict(),
        }


@dataclass(frozen=True)
class VipConfig:
    ip: str
    mac: str


@dataclass
class FlowBinding:
    backend_name: str
    created_at: float
    last_seen_at: float
    expires_at: float
