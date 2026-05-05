"""Module 7: Adaptive Security Enforcement."""
from .continuous_auth import AuthDecision, SessionSignal, score_session
from .micro_segmentation import MicroSegmentationPolicy, default_policy
from .quarantine import quarantine_intent, quarantine_many
from .suricata_parser import alert_to_intent, parse_eve_line, parse_file
from .threat_intel import ThreatIndicator, ThreatIntelStore
__all__ = [
    "AuthDecision", "SessionSignal", "score_session",
    "MicroSegmentationPolicy", "default_policy",
    "quarantine_intent", "quarantine_many",
    "alert_to_intent", "parse_eve_line", "parse_file",
    "ThreatIndicator", "ThreatIntelStore",
]
