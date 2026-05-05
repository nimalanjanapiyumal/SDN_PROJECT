"""Topology Manager.

Tracks switches and links discovered via Ryu's topology events. Falls back
to an in-memory placeholder model when Ryu is not running, so the REST API
can still answer /api/network/topology in unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from threading import RLock
from typing import Dict, List, Set, Tuple


@dataclass
class SwitchRecord:
    dpid: int
    ports: Set[int] = field(default_factory=set)

    def to_dict(self) -> Dict:
        return {"dpid": self.dpid, "ports": sorted(self.ports)}


@dataclass
class LinkRecord:
    src_dpid: int
    src_port: int
    dst_dpid: int
    dst_port: int

    def to_dict(self) -> Dict:
        return asdict(self)


class TopologyManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._switches: Dict[int, SwitchRecord] = {}
        self._links: Dict[Tuple[int, int, int, int], LinkRecord] = {}

    # ---- switch lifecycle ----
    def add_switch(self, dpid: int, ports: Set[int] | None = None) -> SwitchRecord:
        with self._lock:
            rec = self._switches.get(dpid) or SwitchRecord(dpid=dpid)
            if ports:
                rec.ports.update(ports)
            self._switches[dpid] = rec
            return rec

    def remove_switch(self, dpid: int) -> None:
        with self._lock:
            self._switches.pop(dpid, None)
            for key in list(self._links.keys()):
                if key[0] == dpid or key[2] == dpid:
                    self._links.pop(key, None)

    # ---- link lifecycle ----
    def add_link(self, src_dpid: int, src_port: int, dst_dpid: int, dst_port: int) -> LinkRecord:
        link = LinkRecord(src_dpid, src_port, dst_dpid, dst_port)
        with self._lock:
            self._links[(src_dpid, src_port, dst_dpid, dst_port)] = link
            self.add_switch(src_dpid, {src_port})
            self.add_switch(dst_dpid, {dst_port})
            return link

    def remove_link(self, src_dpid: int, src_port: int, dst_dpid: int, dst_port: int) -> None:
        with self._lock:
            self._links.pop((src_dpid, src_port, dst_dpid, dst_port), None)

    # ---- views ----
    def switches(self) -> List[SwitchRecord]:
        with self._lock:
            return list(self._switches.values())

    def links(self) -> List[LinkRecord]:
        with self._lock:
            return list(self._links.values())

    def to_dict(self) -> Dict:
        return {
            "switches": [s.to_dict() for s in self.switches()],
            "links": [l.to_dict() for l in self.links()],
        }


__all__ = ["SwitchRecord", "LinkRecord", "TopologyManager"]
