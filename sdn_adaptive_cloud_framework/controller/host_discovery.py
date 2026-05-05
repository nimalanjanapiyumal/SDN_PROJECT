"""Host Discovery Module.

Tracks every host the controller has learned via PacketIn events and exposes
a thread-safe view that the REST API can query.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from threading import RLock
from typing import Dict, Iterable, List, Optional
import time


@dataclass
class HostRecord:
    mac: str
    ip: Optional[str]
    dpid: int          # datapath ID of the switch the host attaches to
    port: int          # ingress port
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    segment: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class HostRegistry:
    """In-memory host store keyed by MAC address."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._hosts: Dict[str, HostRecord] = {}

    def upsert(
        self,
        mac: str,
        dpid: int,
        port: int,
        ip: Optional[str] = None,
        segment: Optional[str] = None,
    ) -> HostRecord:
        with self._lock:
            now = time.time()
            existing = self._hosts.get(mac)
            if existing is None:
                rec = HostRecord(mac=mac, ip=ip, dpid=dpid, port=port, segment=segment)
                self._hosts[mac] = rec
                return rec
            existing.dpid = dpid
            existing.port = port
            existing.last_seen = now
            if ip:
                existing.ip = ip
            if segment:
                existing.segment = segment
            return existing

    def get_by_mac(self, mac: str) -> Optional[HostRecord]:
        with self._lock:
            return self._hosts.get(mac)

    def get_by_ip(self, ip: str) -> Optional[HostRecord]:
        with self._lock:
            for rec in self._hosts.values():
                if rec.ip == ip:
                    return rec
            return None

    def all(self) -> List[HostRecord]:
        with self._lock:
            return list(self._hosts.values())

    def remove_stale(self, max_age_sec: float) -> List[HostRecord]:
        cutoff = time.time() - max_age_sec
        removed: List[HostRecord] = []
        with self._lock:
            for mac in list(self._hosts.keys()):
                if self._hosts[mac].last_seen < cutoff:
                    removed.append(self._hosts.pop(mac))
        return removed

    def to_list_dict(self) -> List[Dict]:
        return [h.to_dict() for h in self.all()]


__all__ = ["HostRecord", "HostRegistry"]
