"""Continuous authentication risk scoring (Module 7.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SessionSignal:
    src_ip: str
    device_id: str
    duration_sec: float = 0.0
    failed_attempts: int = 0
    unusual_pattern: bool = False
    geo_change: bool = False
    after_hours: bool = False


@dataclass
class AuthDecision:
    risk_score: int
    action: str           # "allow" | "challenge" | "quarantine"
    reasons: List[str] = field(default_factory=list)


def score_session(signal: SessionSignal) -> AuthDecision:
    score = 0
    reasons: List[str] = []

    if signal.failed_attempts > 0:
        delta = min(40, signal.failed_attempts * 8)
        score += delta
        reasons.append(f"failed_attempts={signal.failed_attempts} (+{delta})")

    if signal.unusual_pattern:
        score += 25
        reasons.append("unusual_traffic_pattern (+25)")

    if signal.geo_change:
        score += 20
        reasons.append("geo_change (+20)")

    if signal.after_hours:
        score += 10
        reasons.append("after_hours (+10)")

    if signal.duration_sec > 4 * 3600:
        score += 5
        reasons.append("long_session (+5)")

    if score >= 60:
        action = "quarantine"
    elif score >= 30:
        action = "challenge"
    else:
        action = "allow"

    return AuthDecision(risk_score=score, action=action, reasons=reasons)


def to_intent(decision: AuthDecision, signal: SessionSignal) -> Optional[Dict]:
    """Map a high-risk decision into a controller intent (drop rule)."""
    if decision.action != "quarantine":
        return None
    return {
        "intent_type": "security",
        "action": "quarantine",
        "src_ip": signal.src_ip,
        "priority": 200,
        "description": f"continuous-auth quarantine score={decision.risk_score}",
    }


__all__ = ["SessionSignal", "AuthDecision", "score_session", "to_intent"]
