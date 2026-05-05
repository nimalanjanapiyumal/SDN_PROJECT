"""Dependency-free self-test (no pytest / no fastapi required).

Run from the project root::

    python3 -m sdn_adaptive_cloud_framework.tests.selftest

Exercises the same assertions as the pytest suite for the modules that have
no third-party dependencies, so the framework can be sanity-checked even on
machines that lack pytest/fastapi/sklearn.
"""
from __future__ import annotations

import sys
import traceback
from typing import Callable, List, Tuple


def _check(name: str, fn: Callable[[], None], failures: List[Tuple[str, str]]) -> None:
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception:
        failures.append((name, traceback.format_exc()))
        print(f"  FAIL  {name}")


def main() -> int:
    failures: List[Tuple[str, str]] = []

    # ---- intent processor ----
    from sdn_adaptive_cloud_framework.controller import (
        validate_intent, translate_intent, IntentValidationError,
    )

    def t_validate_basic():
        i = validate_intent({
            "intent_type": "security", "action": "block",
            "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 10,
        })
        assert i.intent_type == "security" and i.action == "block" and i.priority == 10

    def t_translate_outline_example():
        i = validate_intent({
            "intent_type": "security", "action": "block",
            "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 100,
        })
        out = translate_intent(i)
        assert out["flow_action"] == "drop"
        assert out["match"]["ipv4_src"] == "10.0.0.5"
        assert out["match"]["ipv4_dst"] == "10.0.0.10"
        assert out["match"]["eth_type"] == 0x0800
        assert out["priority"] == 100

    def t_invalid_ip_rejected():
        try:
            validate_intent({"intent_type": "security", "action": "block",
                             "src_ip": "not-an-ip"})
        except IntentValidationError:
            return
        raise AssertionError("expected IntentValidationError")

    def t_unknown_combo_rejected():
        try:
            validate_intent({"intent_type": "security", "action": "balance"})
        except IntentValidationError:
            return
        raise AssertionError("expected IntentValidationError")

    print("intent_processor:")
    _check("validate_basic_security_block", t_validate_basic, failures)
    _check("translate_matches_outline_example", t_translate_outline_example, failures)
    _check("invalid_ip_rejected", t_invalid_ip_rejected, failures)
    _check("unknown_combo_rejected", t_unknown_combo_rejected, failures)

    # ---- DFPS ----
    from sdn_adaptive_cloud_framework.controller import (
        rank_intents, NetworkContext, detect_conflicts,
    )

    def t_threat_high_boosts_security():
        intent = validate_intent({"intent_type": "security", "action": "block",
                                  "src_ip": "10.0.0.5"})
        hi = rank_intents([intent], NetworkContext(threat="high"))[0]
        lo = rank_intents([intent], NetworkContext(threat="low"))[0]
        assert hi.final_priority > lo.final_priority and hi.boost == 50

    def t_security_beats_lb_under_threat():
        sec = validate_intent({"intent_type": "security", "action": "block",
                               "src_ip": "10.0.0.5"})
        lb = validate_intent({"intent_type": "load_balancing", "action": "balance",
                              "src_ip": "10.0.0.5"})
        ranked = rank_intents([lb, sec], NetworkContext(threat="high", congestion="high"))
        assert ranked[0].intent.intent_type == "security"

    def t_conflict_detection():
        a = validate_intent({"intent_type": "security", "action": "block",
                             "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10"})
        b = validate_intent({"intent_type": "monitoring", "action": "allow",
                             "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10"})
        c = detect_conflicts([a, b])
        assert (a.intent_id, b.intent_id) in c or (b.intent_id, a.intent_id) in c

    print("dfps_engine:")
    _check("threat_high_boosts_security", t_threat_high_boosts_security, failures)
    _check("security_beats_lb_under_threat", t_security_beats_lb_under_threat, failures)
    _check("conflict_detection", t_conflict_detection, failures)

    # ---- controller state pipeline ----
    from sdn_adaptive_cloud_framework.controller import reset_state_for_tests

    def t_state_submit_installs_record():
        s = reset_state_for_tests()
        r = s.submit_intent({"intent_type": "security", "action": "block",
                             "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10",
                             "priority": 50})
        assert r["records"] and r["translated"]["flow_action"] == "drop"
        assert s.flow_manager.list_records()

    def t_state_context_changes_priority():
        s = reset_state_for_tests()
        s.submit_intent({"intent_type": "load_balancing", "action": "balance"})
        before = rank_intents(s.list_intents(), s.context)[0].final_priority
        s.update_context({"congestion": "high"})
        after = rank_intents(s.list_intents(), s.context)[0].final_priority
        assert after > before

    print("controller_state:")
    _check("state_submit_installs_record", t_state_submit_installs_record, failures)
    _check("state_context_changes_priority", t_state_context_changes_priority, failures)

    # ---- load balancer ----
    from sdn_adaptive_cloud_framework.load_balancer import (
        ServerPool, ServerStatus, HybridLoadBalancer, GAConfig, optimise_server_order,
    )

    def _pool() -> ServerPool:
        return ServerPool([
            ServerStatus("vm1", "10.0.0.11", cpu=45, memory=60, bandwidth=70,
                         active_connections=12),
            ServerStatus("vm2", "10.0.0.12", cpu=80, memory=75, bandwidth=90,
                         active_connections=28),
            ServerStatus("vm3", "10.0.0.13", cpu=20, memory=30, bandwidth=25,
                         active_connections=5),
        ])

    def t_load_score_formula():
        s = ServerStatus("vm1", "10.0.0.11", cpu=50, memory=40,
                         bandwidth=60, active_connections=20, max_connections=100)
        expected = 0.35 * 50 + 0.25 * 40 + 0.25 * 60 + 0.15 * 20
        assert abs(s.load_score() - expected) < 1e-6

    def t_ga_orders_lightest_first():
        ordered = optimise_server_order(
            _pool().all(), GAConfig(seed=42, population_size=10, generations=20)
        )
        assert ordered[0].server_id == "vm3"

    def t_hybrid_select_returns_decision():
        lb = HybridLoadBalancer(_pool(), ga_interval_seconds=0.0,
                                ga_config=GAConfig(seed=1, population_size=10, generations=10))
        d = lb.select(force_ga=True)
        assert d and d["selected_server"] in {"vm1", "vm2", "vm3"}

    def t_unhealthy_skipped():
        pool = _pool()
        pool.update_metrics("vm3", healthy=False)
        lb = HybridLoadBalancer(pool, ga_interval_seconds=0.0)
        seen = set()
        for _ in range(5):
            d = lb.select(force_ga=True)
            if d:
                seen.add(d["selected_server"])
        assert "vm3" not in seen

    print("load_balancer:")
    _check("load_score_formula", t_load_score_formula, failures)
    _check("ga_orders_lightest_first", t_ga_orders_lightest_first, failures)
    _check("hybrid_select_returns_decision", t_hybrid_select_returns_decision, failures)
    _check("unhealthy_servers_skipped", t_unhealthy_skipped, failures)

    # ---- security ----
    from sdn_adaptive_cloud_framework.security import (
        default_policy, score_session, SessionSignal,
        ThreatIntelStore, ThreatIndicator, parse_eve_line, alert_to_intent,
    )

    def t_continuous_auth_quarantine():
        d = score_session(SessionSignal(src_ip="10.0.0.5", device_id="d1",
                                        failed_attempts=5, unusual_pattern=True,
                                        geo_change=True))
        assert d.action == "quarantine" and d.risk_score >= 60

    def t_continuous_auth_normal_allow():
        d = score_session(SessionSignal(src_ip="10.0.0.5", device_id="d1"))
        assert d.action == "allow"

    def t_threat_intel_emits_block():
        s = ThreatIntelStore(70)
        out = s.ingest([ThreatIndicator("185.10.20.30", "botnet", 95)])
        assert out and out[0]["action"] == "block" and out[0]["src_ip"] == "185.10.20.30"

    def t_threat_intel_low_filtered():
        assert ThreatIntelStore(70).ingest([ThreatIndicator("1.2.3.4", "botnet", 30)]) == []

    def t_micro_seg_default_policy():
        p = default_policy()
        assert p.is_allowed("web", "app") and not p.is_allowed("untrusted", "db")

    def t_suricata_alert_to_intent():
        line = ('{"event_type": "alert", "src_ip": "1.2.3.4", "dest_ip": "10.0.0.1", '
                '"alert": {"signature": "ET TROJAN", "severity": 1}}')
        evt = parse_eve_line(line)
        intent = alert_to_intent(evt)
        assert intent["action"] == "block" and intent["priority"] == 240

    print("security:")
    _check("continuous_auth_quarantine", t_continuous_auth_quarantine, failures)
    _check("continuous_auth_normal_allow", t_continuous_auth_normal_allow, failures)
    _check("threat_intel_emits_block", t_threat_intel_emits_block, failures)
    _check("threat_intel_low_filtered", t_threat_intel_low_filtered, failures)
    _check("micro_seg_default_policy", t_micro_seg_default_policy, failures)
    _check("suricata_alert_to_intent", t_suricata_alert_to_intent, failures)

    # ---- ML heuristic ----
    from sdn_adaptive_cloud_framework.ml_module import HeuristicModel

    def t_ml_high_load():
        out = HeuristicModel().predict({
            "latency_ms": 220, "throughput_mbps": 100, "packet_loss": 5,
            "cpu_usage": 92, "memory_usage": 80, "flow_count": 800,
        })
        assert out["risk_level"] == "high" and out["prediction"] == "congestion_risk"

    def t_ml_normal():
        out = HeuristicModel().predict({
            "latency_ms": 12, "throughput_mbps": 950, "packet_loss": 0.1,
            "cpu_usage": 30, "memory_usage": 40, "flow_count": 50,
        })
        assert out["risk_level"] == "low"

    print("ml_module:")
    _check("ml_high_load", t_ml_high_load, failures)
    _check("ml_normal", t_ml_normal, failures)

    print()
    if failures:
        print(f"{len(failures)} failure(s):")
        for name, tb in failures:
            print(f"--- {name} ---\n{tb}")
        return 1
    print("ALL SELFTESTS PASSED")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
