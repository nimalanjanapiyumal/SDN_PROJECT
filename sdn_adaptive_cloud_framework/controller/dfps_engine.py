"""Dynamic Flow Priority Scheduling Engine (Module 3).

Resolves conflicts between competing intents by combining each intent's
base priority with context-driven boosts (threat level, congestion, latency,
SLA risk).  Returns an ordered list ready for installation.

The rules implemented here mirror the example logic in the development
outline (section "Module 3 - Dynamic Flow Priority Scheduling").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .intent_processor import Intent, IntentType


@dataclass
class NetworkContext:
    """Snapshot of context signals used to compute priority boosts."""
    threat: str = "low"            # one of: low / medium / high
    congestion: str = "low"        # one of: low / medium / high
    sla_risk: str = "low"          # one of: low / medium / high
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    extras: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "NetworkContext":
        if not data:
            return cls()
        return cls(
            threat=str(data.get("threat", "low")).lower(),
            congestion=str(data.get("congestion", "low")).lower(),
            sla_risk=str(data.get("sla_risk", "low")).lower(),
            latency_ms=float(data.get("latency_ms", 0.0)),
            packet_loss=float(data.get("packet_loss", 0.0)),
            cpu_usage=float(data.get("cpu_usage", 0.0)),
            memory_usage=float(data.get("memory_usage", 0.0)),
            extras={k: v for k, v in data.items() if k not in {
                "threat", "congestion", "sla_risk", "latency_ms",
                "packet_loss", "cpu_usage", "memory_usage",
            }},
        )


# Static ranking applied as a tiebreaker. Lower value = higher precedence.
_TYPE_RANK: Dict[str, int] = {
    IntentType.SECURITY.value:       1,  # Security enforcement
    IntentType.SEGMENTATION.value:   2,  # SLA / isolation guarantees
    IntentType.MONITORING.value:     3,  # Congestion avoidance
    IntentType.LOAD_BALANCING.value: 4,  # Load balancing
    IntentType.OPTIMIZATION.value:   5,  # General optimization
}


def _level_to_int(level: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(level, 0)


def compute_priority_boost(intent: Intent, context: NetworkContext) -> int:
    """Compute a context-driven priority boost for one intent."""
    boost = 0

    if intent.intent_type == IntentType.SECURITY.value and context.threat == "high":
        boost += 50
    elif intent.intent_type == IntentType.SECURITY.value and context.threat == "medium":
        boost += 25

    if intent.intent_type == IntentType.LOAD_BALANCING.value and context.congestion == "high":
        boost += 30
    elif intent.intent_type == IntentType.LOAD_BALANCING.value and context.congestion == "medium":
        boost += 15

    if intent.intent_type == IntentType.OPTIMIZATION.value and context.latency_ms > 100:
        boost += 20

    if intent.intent_type == IntentType.SEGMENTATION.value and context.threat in {"medium", "high"}:
        boost += 15

    if context.sla_risk == "high" and intent.intent_type in {
        IntentType.OPTIMIZATION.value,
        IntentType.LOAD_BALANCING.value,
    }:
        boost += 25

    return boost


@dataclass
class RankedIntent:
    intent: Intent
    final_priority: int
    boost: int
    type_rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent.intent_id,
            "intent_type": self.intent.intent_type,
            "base_priority": self.intent.priority,
            "boost": self.boost,
            "final_priority": self.final_priority,
            "type_rank": self.type_rank,
        }


def rank_intents(
    intents: Iterable[Intent],
    context: Optional[NetworkContext] = None,
) -> List[RankedIntent]:
    """Return intents sorted from highest to lowest installation priority."""
    context = context or NetworkContext()
    ranked: List[RankedIntent] = []
    for intent in intents:
        boost = compute_priority_boost(intent, context)
        # Clamp final priority into the OF priority range.
        final = max(0, min(65535, intent.priority + boost))
        ranked.append(RankedIntent(
            intent=intent,
            final_priority=final,
            boost=boost,
            type_rank=_TYPE_RANK.get(intent.intent_type, 99),
        ))

    # Sort: higher final_priority first, then lower type_rank as tiebreaker,
    # then earlier submission as final tiebreaker.
    ranked.sort(key=lambda r: (-r.final_priority, r.type_rank, r.intent.submitted_at))
    return ranked


def detect_conflicts(intents: Iterable[Intent]) -> List[Tuple[str, str]]:
    """Identify intent pairs that match the same flow with opposing actions.

    Returns a list of (intent_id_a, intent_id_b) pairs where one intent
    drops a flow and another forwards the same flow.
    """
    intent_list = list(intents)
    conflicts: List[Tuple[str, str]] = []
    for i, a in enumerate(intent_list):
        for b in intent_list[i + 1:]:
            if a.src_ip != b.src_ip or a.dst_ip != b.dst_ip:
                continue
            if a.protocol and b.protocol and a.protocol != b.protocol:
                continue
            opposing = {
                ("block", "allow"),
                ("allow", "block"),
                ("quarantine", "allow"),
                ("allow", "quarantine"),
            }
            if (a.action, b.action) in opposing:
                conflicts.append((a.intent_id, b.intent_id))
    return conflicts


__all__ = [
    "NetworkContext",
    "RankedIntent",
    "compute_priority_boost",
    "rank_intents",
    "detect_conflicts",
]
