"""Dynamic threat-intelligence ingestion (Module 7.3)."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, Iterable, List, Optional


@dataclass
class ThreatIndicator:
    malicious_ip: str
    threat_type: str = "unknown"
    confidence: int = 0      # 0..100


class ThreatIntelStore:
    def __init__(self, min_confidence: int = 70) -> None:
        self._lock = RLock()
        self._items: Dict[str, ThreatIndicator] = {}
        self.min_confidence = min_confidence

    def ingest(self, indicators: Iterable[ThreatIndicator]) -> List[Dict]:
        """Add indicators and return controller-ready block intents."""
        produced: List[Dict] = []
        with self._lock:
            for ind in indicators:
                self._items[ind.malicious_ip] = ind
                if ind.confidence >= self.min_confidence:
                    produced.append({
                        "intent_type": "security",
                        "action": "block",
                        "src_ip": ind.malicious_ip,
                        "priority": 220,
                        "description": f"CTI {ind.threat_type} ({ind.confidence}%)",
                    })
        return produced

    def list(self) -> List[ThreatIndicator]:
        with self._lock:
            return list(self._items.values())

    def lookup(self, ip: str) -> Optional[ThreatIndicator]:
        with self._lock:
            return self._items.get(ip)


__all__ = ["ThreatIndicator", "ThreatIntelStore"]
