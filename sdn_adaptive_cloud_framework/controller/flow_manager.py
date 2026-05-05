"""Flow Rule Manager.

Bridges the controller's logical view (intents, segmentation rules, LB
decisions) with concrete OpenFlow flow-mod messages. Designed so the same
``FlowManager`` API can be driven by the live Ryu controller *and* by the
REST/unit-test layer where Ryu may be absent. When Ryu is unavailable the
manager only records the rule; when Ryu is available it additionally builds
and sends an OFPFlowMod via the registered datapath.

Records are addressable by ``intent_id`` so that the API can later remove
the matching flow with ``DELETE /api/flow/{intent_id}``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from threading import RLock
from typing import Any, Dict, List, Optional
import time
import uuid


@dataclass
class FlowRecord:
    rule_id: str
    intent_id: Optional[str]
    dpid: int
    match: Dict[str, Any]
    flow_action: str           # "drop" | "forward"
    priority: int
    out_port: Optional[int] = None
    next_hop_ip: Optional[str] = None
    installed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Try to import Ryu lazily; the framework still works when Ryu is missing
# (e.g. in CI / unit tests). Production runs use Ryu's eventlet runtime.
try:  # pragma: no cover - exercised on Mininet host only
    from ryu.ofproto import ofproto_v1_3 as _ofproto
    from ryu.ofproto import ofproto_v1_3_parser as _parser
    _RYU_AVAILABLE = True
except Exception:  # pragma: no cover
    _ofproto = None  # type: ignore[assignment]
    _parser = None   # type: ignore[assignment]
    _RYU_AVAILABLE = False


class FlowManager:
    """Stores and applies flow rules across all known datapaths."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: Dict[str, FlowRecord] = {}
        self._datapaths: Dict[int, Any] = {}

    # ---- datapath registration ----
    def register_datapath(self, datapath: Any) -> None:
        if datapath is None:
            return
        with self._lock:
            self._datapaths[int(datapath.id)] = datapath

    def unregister_datapath(self, dpid: int) -> None:
        with self._lock:
            self._datapaths.pop(int(dpid), None)

    def known_dpids(self) -> List[int]:
        with self._lock:
            return list(self._datapaths.keys())

    # ---- record lifecycle ----
    def install(
        self,
        match: Dict[str, Any],
        flow_action: str,
        priority: int,
        intent_id: Optional[str] = None,
        dpid: Optional[int] = None,
        out_port: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[FlowRecord]:
        """Install one rule on the requested dpid (or on all known dpids)."""
        records: List[FlowRecord] = []
        target_dpids: List[int]
        with self._lock:
            target_dpids = [dpid] if dpid is not None else list(self._datapaths.keys()) or [0]

        for target in target_dpids:
            record = FlowRecord(
                rule_id=str(uuid.uuid4()),
                intent_id=intent_id,
                dpid=target,
                match=dict(match),
                flow_action=flow_action,
                priority=priority,
                out_port=out_port,
                metadata=dict(metadata or {}),
            )
            with self._lock:
                self._records[record.rule_id] = record
            self._push_to_datapath(record)
            records.append(record)
        return records

    def remove_by_intent(self, intent_id: str) -> List[FlowRecord]:
        removed: List[FlowRecord] = []
        with self._lock:
            for rid in list(self._records.keys()):
                if self._records[rid].intent_id == intent_id:
                    removed.append(self._records.pop(rid))
        for rec in removed:
            self._delete_from_datapath(rec)
        return removed

    def remove_by_rule_id(self, rule_id: str) -> Optional[FlowRecord]:
        with self._lock:
            rec = self._records.pop(rule_id, None)
        if rec is not None:
            self._delete_from_datapath(rec)
        return rec

    def list_records(self) -> List[FlowRecord]:
        with self._lock:
            return list(self._records.values())

    # ---- datapath I/O ----
    def _push_to_datapath(self, rec: FlowRecord) -> None:  # pragma: no cover - live-only
        if not _RYU_AVAILABLE:
            return
        with self._lock:
            datapath = self._datapaths.get(rec.dpid)
        if datapath is None:
            return
        match = self._build_ryu_match(datapath, rec.match)
        actions = self._build_ryu_actions(datapath, rec)
        instructions = [
            _parser.OFPInstructionActions(_ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        flow_mod = _parser.OFPFlowMod(
            datapath=datapath,
            priority=rec.priority,
            match=match,
            instructions=instructions,
            command=_ofproto.OFPFC_ADD,
            idle_timeout=0,
            hard_timeout=0,
        )
        datapath.send_msg(flow_mod)

    def _delete_from_datapath(self, rec: FlowRecord) -> None:  # pragma: no cover - live-only
        if not _RYU_AVAILABLE:
            return
        with self._lock:
            datapath = self._datapaths.get(rec.dpid)
        if datapath is None:
            return
        match = self._build_ryu_match(datapath, rec.match)
        flow_mod = _parser.OFPFlowMod(
            datapath=datapath,
            priority=rec.priority,
            match=match,
            command=_ofproto.OFPFC_DELETE_STRICT,
            out_port=_ofproto.OFPP_ANY,
            out_group=_ofproto.OFPG_ANY,
        )
        datapath.send_msg(flow_mod)

    @staticmethod
    def _build_ryu_match(datapath: Any, match: Dict[str, Any]):  # pragma: no cover
        parser = datapath.ofproto_parser
        return parser.OFPMatch(**match)

    @staticmethod
    def _build_ryu_actions(datapath: Any, rec: FlowRecord):  # pragma: no cover
        parser = datapath.ofproto_parser
        ofp = datapath.ofproto
        if rec.flow_action == "drop":
            return []
        out_port = rec.out_port if rec.out_port is not None else ofp.OFPP_NORMAL
        return [parser.OFPActionOutput(out_port)]


__all__ = ["FlowRecord", "FlowManager"]
