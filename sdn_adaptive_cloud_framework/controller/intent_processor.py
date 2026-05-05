"""Intent Processing Engine (Module 2).

Validates user-submitted intents and translates them into OpenFlow-compatible
match/action dictionaries that the Flow Rule Manager can install on switches.

The schemas in this module mirror the input/output examples in the development
outline, section "Module 2 - Intent Processing Engine".
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import ipaddress
import re
import time
import uuid


class IntentType(str, Enum):
    """Categories of intents recognised by the controller."""
    SECURITY = "security"
    LOAD_BALANCING = "load_balancing"
    MONITORING = "monitoring"
    SEGMENTATION = "segmentation"
    OPTIMIZATION = "optimization"


class IntentAction(str, Enum):
    BLOCK = "block"
    ALLOW = "allow"
    REROUTE = "reroute"
    QUARANTINE = "quarantine"
    BALANCE = "balance"
    MONITOR = "monitor"
    SEGMENT = "segment"


# Map (intent_type, action) -> default OpenFlow action verb. The flow_manager
# converts these verbs into datapath-specific OFPAction* objects.
_FLOW_ACTION_MAP: Dict[Tuple[str, str], str] = {
    (IntentType.SECURITY.value, IntentAction.BLOCK.value): "drop",
    (IntentType.SECURITY.value, IntentAction.QUARANTINE.value): "drop",
    (IntentType.SECURITY.value, IntentAction.ALLOW.value): "forward",
    (IntentType.SEGMENTATION.value, IntentAction.BLOCK.value): "drop",
    (IntentType.SEGMENTATION.value, IntentAction.ALLOW.value): "forward",
    (IntentType.LOAD_BALANCING.value, IntentAction.BALANCE.value): "forward",
    (IntentType.LOAD_BALANCING.value, IntentAction.REROUTE.value): "forward",
    (IntentType.OPTIMIZATION.value, IntentAction.REROUTE.value): "forward",
    (IntentType.MONITORING.value, IntentAction.MONITOR.value): "forward",
    (IntentType.MONITORING.value, IntentAction.ALLOW.value): "forward",
}


# Default base priorities per intent_type. DFPS may bump these dynamically
# based on real-time context (threat/congestion/SLA), but these are the
# floor priorities that ensure rules install in a sane order even when no
# context has been received yet.
DEFAULT_BASE_PRIORITY: Dict[str, int] = {
    IntentType.SECURITY.value: 100,
    IntentType.SEGMENTATION.value: 90,
    IntentType.MONITORING.value: 60,
    IntentType.OPTIMIZATION.value: 40,
    IntentType.LOAD_BALANCING.value: 30,
}


@dataclass
class Intent:
    """Validated intent record kept in the controller's local store."""
    intent_id: str
    intent_type: str
    action: str
    priority: int
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    protocol: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    src_segment: Optional[str] = None
    dst_segment: Optional[str] = None
    next_hop_ip: Optional[str] = None
    description: Optional[str] = None
    submitted_at: float = field(default_factory=time.time)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IntentValidationError(ValueError):
    """Raised when an intent fails schema validation."""


_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _is_ipv4(value: Optional[str]) -> bool:
    if value is None:
        return False
    try:
        ipaddress.IPv4Address(value)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def validate_intent(payload: Dict[str, Any]) -> Intent:
    """Validate a raw intent payload and return a normalised Intent record."""
    if not isinstance(payload, dict):
        raise IntentValidationError("Intent payload must be a JSON object")

    intent_type = str(payload.get("intent_type", "")).strip().lower()
    if intent_type not in {t.value for t in IntentType}:
        raise IntentValidationError(
            f"intent_type must be one of {[t.value for t in IntentType]}"
        )

    action = str(payload.get("action", "")).strip().lower()
    if action not in {a.value for a in IntentAction}:
        raise IntentValidationError(
            f"action must be one of {[a.value for a in IntentAction]}"
        )

    if (intent_type, action) not in _FLOW_ACTION_MAP:
        raise IntentValidationError(
            f"action '{action}' is not valid for intent_type '{intent_type}'"
        )

    src_ip = payload.get("src_ip")
    dst_ip = payload.get("dst_ip")
    if src_ip is not None and not _is_ipv4(src_ip):
        raise IntentValidationError(f"src_ip is not a valid IPv4 address: {src_ip!r}")
    if dst_ip is not None and not _is_ipv4(dst_ip):
        raise IntentValidationError(f"dst_ip is not a valid IPv4 address: {dst_ip!r}")

    raw_priority = payload.get("priority")
    if raw_priority is None:
        priority = DEFAULT_BASE_PRIORITY.get(intent_type, 10)
    else:
        try:
            priority = int(raw_priority)
        except (TypeError, ValueError) as exc:
            raise IntentValidationError("priority must be an integer") from exc
        if not 0 <= priority <= 65535:
            raise IntentValidationError("priority must be in [0, 65535]")

    src_port = payload.get("src_port")
    dst_port = payload.get("dst_port")
    for label, value in (("src_port", src_port), ("dst_port", dst_port)):
        if value is not None and not (isinstance(value, int) and 0 <= value <= 65535):
            raise IntentValidationError(f"{label} must be an int in [0, 65535]")

    return Intent(
        intent_id=str(payload.get("intent_id") or uuid.uuid4()),
        intent_type=intent_type,
        action=action,
        priority=priority,
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=payload.get("protocol"),
        src_port=src_port,
        dst_port=dst_port,
        src_segment=payload.get("src_segment"),
        dst_segment=payload.get("dst_segment"),
        next_hop_ip=payload.get("next_hop_ip"),
        description=payload.get("description"),
        raw=dict(payload),
    )


def _proto_match(intent: Intent) -> Dict[str, Any]:
    """Return the L4 portion of a match dict, if any."""
    match: Dict[str, Any] = {}
    proto = (intent.protocol or "").lower() if intent.protocol else ""
    if proto in {"tcp", "udp"}:
        match["ip_proto"] = 6 if proto == "tcp" else 17
        if intent.src_port is not None:
            match[f"{proto}_src"] = intent.src_port
        if intent.dst_port is not None:
            match[f"{proto}_dst"] = intent.dst_port
    elif proto == "icmp":
        match["ip_proto"] = 1
    return match


def translate_intent(intent: Intent) -> Dict[str, Any]:
    """Translate an Intent into an OpenFlow-compatible action descriptor.

    Output shape::

        {
            "intent_id": "...",
            "flow_action": "drop" | "forward",
            "match": { "eth_type": 0x0800, "ipv4_src": "...", ... },
            "priority": 100,
            "next_hop_ip": "...",
            "metadata": { "intent_type": "...", "action": "..." }
        }
    """
    flow_action = _FLOW_ACTION_MAP[(intent.intent_type, intent.action)]

    match: Dict[str, Any] = {}
    if intent.src_ip or intent.dst_ip or intent.protocol:
        match["eth_type"] = 0x0800  # IPv4

    if intent.src_ip:
        match["ipv4_src"] = intent.src_ip
    if intent.dst_ip:
        match["ipv4_dst"] = intent.dst_ip
    match.update(_proto_match(intent))

    return {
        "intent_id": intent.intent_id,
        "flow_action": flow_action,
        "match": match,
        "priority": intent.priority,
        "next_hop_ip": intent.next_hop_ip,
        "metadata": {
            "intent_type": intent.intent_type,
            "action": intent.action,
            "src_segment": intent.src_segment,
            "dst_segment": intent.dst_segment,
            "description": intent.description,
        },
    }


class IntentStore:
    """In-memory store of submitted intents.

    A real deployment would persist these (sqlite/redis); for the framework
    skeleton an in-memory dict is sufficient and is exercised by the unit
    tests in tests/test_controller.py.
    """

    def __init__(self) -> None:
        self._intents: Dict[str, Intent] = {}

    def add(self, intent: Intent) -> None:
        self._intents[intent.intent_id] = intent

    def get(self, intent_id: str) -> Optional[Intent]:
        return self._intents.get(intent_id)

    def remove(self, intent_id: str) -> Optional[Intent]:
        return self._intents.pop(intent_id, None)

    def list(self, intent_type: Optional[str] = None) -> List[Intent]:
        if intent_type is None:
            return list(self._intents.values())
        return [i for i in self._intents.values() if i.intent_type == intent_type]


__all__ = [
    "Intent",
    "IntentType",
    "IntentAction",
    "IntentStore",
    "IntentValidationError",
    "DEFAULT_BASE_PRIORITY",
    "validate_intent",
    "translate_intent",
]
