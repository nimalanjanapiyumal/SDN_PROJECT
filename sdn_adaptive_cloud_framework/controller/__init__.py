"""Module 1: Intelligent SDN Controller package."""
from .controller_state import ControllerState, get_state, reset_state_for_tests
from .dfps_engine import (
    NetworkContext, RankedIntent, compute_priority_boost,
    rank_intents, detect_conflicts,
)
from .flow_manager import FlowManager, FlowRecord
from .host_discovery import HostRecord, HostRegistry
from .intent_processor import (
    DEFAULT_BASE_PRIORITY, Intent, IntentAction, IntentStore,
    IntentType, IntentValidationError, translate_intent, validate_intent,
)
from .topology_manager import LinkRecord, SwitchRecord, TopologyManager

__all__ = [
    "ControllerState", "get_state", "reset_state_for_tests",
    "Intent", "IntentType", "IntentAction", "IntentStore",
    "IntentValidationError", "DEFAULT_BASE_PRIORITY",
    "validate_intent", "translate_intent",
    "NetworkContext", "RankedIntent", "rank_intents",
    "compute_priority_boost", "detect_conflicts",
    "FlowManager", "FlowRecord",
    "HostRecord", "HostRegistry",
    "SwitchRecord", "LinkRecord", "TopologyManager",
]
