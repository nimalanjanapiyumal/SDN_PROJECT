"""Unit tests for the Intelligent SDN Controller (Module 1)."""
from __future__ import annotations

import pytest

from sdn_adaptive_cloud_framework.controller import (
    IntentValidationError,
    NetworkContext,
    detect_conflicts,
    rank_intents,
    reset_state_for_tests,
    translate_intent,
    validate_intent,
)


def test_validate_intent_basic_security_block():
    payload = {
        "intent_type": "security",
        "action": "block",
        "src_ip": "10.0.0.5",
        "dst_ip": "10.0.0.10",
        "priority": 10,
    }
    intent = validate_intent(payload)
    assert intent.intent_type == "security"
    assert intent.action == "block"
    assert intent.priority == 10


def test_translate_security_block_matches_outline_example():
    """Outline's Module 2 example output: drop with ipv4 match."""
    payload = {
        "intent_type": "security", "action": "block",
        "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 100,
    }
    intent = validate_intent(payload)
    translated = translate_intent(intent)
    assert translated["flow_action"] == "drop"
    assert translated["match"]["ipv4_src"] == "10.0.0.5"
    assert translated["match"]["ipv4_dst"] == "10.0.0.10"
    assert translated["match"]["eth_type"] == 0x0800
    assert translated["priority"] == 100


def test_validate_invalid_ip():
    with pytest.raises(IntentValidationError):
        validate_intent({"intent_type": "security", "action": "block", "src_ip": "not-an-ip"})


def test_validate_unknown_combination_rejected():
    with pytest.raises(IntentValidationError):
        validate_intent({"intent_type": "security", "action": "balance"})


def test_dfps_threat_high_boosts_security():
    base = validate_intent({"intent_type": "security", "action": "block",
                            "src_ip": "10.0.0.5"})
    ranked_high = rank_intents([base], NetworkContext(threat="high"))
    ranked_low = rank_intents([base], NetworkContext(threat="low"))
    assert ranked_high[0].final_priority > ranked_low[0].final_priority
    assert ranked_high[0].boost == 50


def test_dfps_security_beats_load_balancing_under_threat():
    sec = validate_intent({"intent_type": "security", "action": "block",
                           "src_ip": "10.0.0.5"})
    lb = validate_intent({"intent_type": "load_balancing", "action": "balance",
                          "src_ip": "10.0.0.5"})
    ranked = rank_intents([lb, sec], NetworkContext(threat="high", congestion="high"))
    assert ranked[0].intent.intent_type == "security"


def test_detect_conflicts_block_vs_allow():
    a = validate_intent({"intent_type": "security", "action": "block",
                         "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10"})
    b = validate_intent({"intent_type": "monitoring", "action": "allow",
                         "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10"})
    conflicts = detect_conflicts([a, b])
    assert (a.intent_id, b.intent_id) in conflicts or (b.intent_id, a.intent_id) in conflicts


def test_state_submit_intent_installs_record():
    state = reset_state_for_tests()
    result = state.submit_intent({
        "intent_type": "security", "action": "block",
        "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 50,
    })
    assert result["records"], "expected at least one flow record"
    assert result["translated"]["flow_action"] == "drop"
    assert state.flow_manager.list_records()


def test_state_context_update_changes_ranking():
    state = reset_state_for_tests()
    state.submit_intent({"intent_type": "load_balancing", "action": "balance"})
    before = rank_intents(state.list_intents(), state.context)[0].final_priority
    state.update_context({"congestion": "high"})
    after = rank_intents(state.list_intents(), state.context)[0].final_priority
    assert after > before
