"""Shared controller state.

Holds the singletons (intent store, host registry, topology manager, flow
manager, current network context, latest ML prediction) that the REST API
and the Ryu controller app both read and write. Using one ``ControllerState``
instance avoids the API and the Ryu app drifting out of sync.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional
import time

from .dfps_engine import NetworkContext, rank_intents
from .flow_manager import FlowManager, FlowRecord
from .host_discovery import HostRegistry
from .intent_processor import (
    Intent,
    IntentStore,
    translate_intent,
    validate_intent,
)
from .topology_manager import TopologyManager


@dataclass
class ControllerState:
    intent_store: IntentStore = field(default_factory=IntentStore)
    flow_manager: FlowManager = field(default_factory=FlowManager)
    hosts: HostRegistry = field(default_factory=HostRegistry)
    topology: TopologyManager = field(default_factory=TopologyManager)
    context: NetworkContext = field(default_factory=NetworkContext)
    last_ml_prediction: Optional[Dict[str, Any]] = None
    _lock: RLock = field(default_factory=RLock)

    # ---- intent + rule pipeline ----
    def submit_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate -> rank with current context -> install flow rule(s)."""
        intent = validate_intent(payload)
        with self._lock:
            self.intent_store.add(intent)
            ranked = rank_intents(self.intent_store.list(), self.context)
            ranked_lookup = {r.intent.intent_id: r for r in ranked}
            ranked_self = ranked_lookup[intent.intent_id]

        translated = translate_intent(intent)
        translated["priority"] = ranked_self.final_priority
        records = self.flow_manager.install(
            match=translated["match"],
            flow_action=translated["flow_action"],
            priority=translated["priority"],
            intent_id=intent.intent_id,
            metadata=translated["metadata"],
        )
        return {
            "intent": intent.to_dict(),
            "translated": translated,
            "ranking": ranked_self.to_dict(),
            "records": [r.to_dict() for r in records],
        }

    def update_context(self, payload: Dict[str, Any]) -> NetworkContext:
        with self._lock:
            self.context = NetworkContext.from_dict(payload)
        return self.context

    def set_ml_prediction(self, payload: Dict[str, Any]) -> None:
        payload = dict(payload)
        payload["received_at"] = time.time()
        self.last_ml_prediction = payload

    def list_intents(self) -> List[Intent]:
        return self.intent_store.list()

    def remove_intent(self, intent_id: str) -> List[FlowRecord]:
        with self._lock:
            self.intent_store.remove(intent_id)
        return self.flow_manager.remove_by_intent(intent_id)


# Module-level singleton used by both the API and the Ryu app.
_STATE: Optional[ControllerState] = None
_STATE_LOCK = RLock()


def get_state() -> ControllerState:
    global _STATE
    with _STATE_LOCK:
        if _STATE is None:
            _STATE = ControllerState()
        return _STATE


def reset_state_for_tests() -> ControllerState:
    """Replace the singleton with a fresh instance (unit-test helper)."""
    global _STATE
    with _STATE_LOCK:
        _STATE = ControllerState()
        return _STATE


__all__ = ["ControllerState", "get_state", "reset_state_for_tests"]
