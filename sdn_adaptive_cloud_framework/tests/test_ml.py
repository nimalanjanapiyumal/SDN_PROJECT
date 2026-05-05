"""Unit tests for the ML prediction module (Module 6)."""
from __future__ import annotations

from sdn_adaptive_cloud_framework.ml_module import HeuristicModel


def test_heuristic_high_load_classified_high_risk():
    out = HeuristicModel().predict({
        "latency_ms": 220, "throughput_mbps": 100, "packet_loss": 5,
        "cpu_usage": 92, "memory_usage": 80, "flow_count": 800,
    })
    assert out["prediction"] == "congestion_risk"
    assert out["risk_level"] == "high"
    assert out["recommended_action"] == "reroute_traffic"


def test_heuristic_normal_traffic_low_risk():
    out = HeuristicModel().predict({
        "latency_ms": 12, "throughput_mbps": 950, "packet_loss": 0.1,
        "cpu_usage": 30, "memory_usage": 40, "flow_count": 50,
    })
    assert out["risk_level"] == "low"
    assert out["prediction"] == "normal"
