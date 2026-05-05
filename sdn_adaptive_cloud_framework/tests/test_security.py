"""Unit tests for the security module (Module 7)."""
from __future__ import annotations

from sdn_adaptive_cloud_framework.security import (
    SessionSignal,
    ThreatIndicator,
    ThreatIntelStore,
    alert_to_intent,
    default_policy,
    parse_eve_line,
    score_session,
)


def test_continuous_auth_quarantines_high_risk():
    decision = score_session(SessionSignal(
        src_ip="10.0.0.5", device_id="dev-01",
        failed_attempts=5, unusual_pattern=True, geo_change=True,
    ))
    assert decision.action == "quarantine"
    assert decision.risk_score >= 60


def test_continuous_auth_allows_normal_session():
    decision = score_session(SessionSignal(src_ip="10.0.0.5", device_id="dev-01"))
    assert decision.action == "allow"


def test_threat_intel_high_confidence_emits_block_intent():
    store = ThreatIntelStore(min_confidence=70)
    intents = store.ingest([ThreatIndicator("185.10.20.30", "botnet", 95)])
    assert intents and intents[0]["action"] == "block"
    assert intents[0]["src_ip"] == "185.10.20.30"


def test_threat_intel_low_confidence_filtered():
    store = ThreatIntelStore(min_confidence=70)
    assert store.ingest([ThreatIndicator("1.2.3.4", "botnet", 30)]) == []


def test_micro_seg_allows_web_to_app_blocks_untrusted():
    p = default_policy()
    assert p.is_allowed("web", "app")
    assert not p.is_allowed("untrusted", "db")


def test_suricata_alert_to_intent():
    line = (
        '{"event_type": "alert", "src_ip": "1.2.3.4", "dest_ip": "10.0.0.1", '
        '"alert": {"signature": "ET TROJAN", "severity": 1}}'
    )
    evt = parse_eve_line(line)
    assert evt is not None
    intent = alert_to_intent(evt)
    assert intent["action"] == "block"
    assert intent["priority"] == 240
