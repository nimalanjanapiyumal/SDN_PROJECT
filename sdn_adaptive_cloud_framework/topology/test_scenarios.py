"""Evaluation scenarios from outline section 11.

These are pure helpers that build the *intent payloads* and *context updates*
needed to reproduce each evaluation scenario against the REST API.

Example::

    from sdn_adaptive_cloud_framework.topology.test_scenarios import scenario_block_malicious_ip
    payload = scenario_block_malicious_ip()
    requests.post("http://127.0.0.1:8080/api/intent/submit", json=payload)
"""
from __future__ import annotations

from typing import Dict, List


def scenario_normal_traffic_context() -> Dict:
    return {
        "threat": "low", "congestion": "low", "sla_risk": "low",
        "latency_ms": 12, "packet_loss": 0.1, "cpu_usage": 30, "memory_usage": 40,
    }


def scenario_high_load_context() -> Dict:
    return {
        "threat": "low", "congestion": "high", "sla_risk": "medium",
        "latency_ms": 220, "packet_loss": 4.0, "cpu_usage": 90, "memory_usage": 80,
    }


def scenario_block_malicious_ip(src_ip: str = "185.10.20.30") -> Dict:
    return {
        "intent_type": "security",
        "action": "block",
        "src_ip": src_ip,
        "priority": 220,
        "description": "scenario 4: malicious source",
    }


def scenario_quarantine_suspicious(src_ip: str = "10.0.4.13") -> Dict:
    return {
        "intent_type": "security",
        "action": "quarantine",
        "src_ip": src_ip,
        "priority": 200,
        "description": "scenario 5: continuous-auth quarantine",
    }


def scenario_lateral_movement_block() -> Dict:
    return {
        "intent_type": "segmentation",
        "action": "block",
        "src_segment": "untrusted",
        "dst_segment": "db",
        "priority": 90,
        "description": "scenario 6: lateral movement block",
    }


def scenario_conflicting_intents() -> List[Dict]:
    return [
        {
            "intent_type": "load_balancing", "action": "balance",
            "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 30,
        },
        {
            "intent_type": "security", "action": "block",
            "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 100,
            "description": "scenario 7: should beat load balancing",
        },
    ]


__all__ = [
    "scenario_normal_traffic_context",
    "scenario_high_load_context",
    "scenario_block_malicious_ip",
    "scenario_quarantine_suspicious",
    "scenario_lateral_movement_block",
    "scenario_conflicting_intents",
]
