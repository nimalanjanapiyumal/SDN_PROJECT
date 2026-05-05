"""Automatic quarantine helpers (Module 7.5)."""
from __future__ import annotations

from typing import Dict, Iterable, List


def quarantine_intent(src_ip: str, reason: str = "automatic-quarantine", priority: int = 250) -> Dict:
    return {
        "intent_type": "security",
        "action": "quarantine",
        "src_ip": src_ip,
        "priority": priority,
        "description": reason,
    }


def quarantine_many(ips: Iterable[str], reason: str = "bulk-quarantine") -> List[Dict]:
    return [quarantine_intent(ip, reason) for ip in ips]


__all__ = ["quarantine_intent", "quarantine_many"]
