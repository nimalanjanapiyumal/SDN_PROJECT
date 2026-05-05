"""Unit tests for the hybrid load balancer (Module 4)."""
from __future__ import annotations

from sdn_adaptive_cloud_framework.load_balancer import (
    GAConfig,
    HybridLoadBalancer,
    ServerPool,
    ServerStatus,
    optimise_server_order,
)


def _pool() -> ServerPool:
    return ServerPool([
        ServerStatus(server_id="vm1", ip="10.0.0.11", cpu=45, memory=60,
                     bandwidth=70, active_connections=12),
        ServerStatus(server_id="vm2", ip="10.0.0.12", cpu=80, memory=75,
                     bandwidth=90, active_connections=28),
        ServerStatus(server_id="vm3", ip="10.0.0.13", cpu=20, memory=30,
                     bandwidth=25, active_connections=5),
    ])


def test_load_score_formula():
    s = ServerStatus(server_id="vm1", ip="10.0.0.11",
                     cpu=50, memory=40, bandwidth=60, active_connections=20,
                     max_connections=100)
    expected = 0.35 * 50 + 0.25 * 40 + 0.25 * 60 + 0.15 * 20
    assert abs(s.load_score() - expected) < 1e-6


def test_ga_orders_lightest_first():
    pool = _pool()
    ordered = optimise_server_order(pool.all(), GAConfig(seed=42, population_size=10, generations=20))
    assert ordered[0].server_id == "vm3"  # lowest load_score


def test_hybrid_lb_select_returns_decision():
    lb = HybridLoadBalancer(_pool(), ga_interval_seconds=0.0,
                            ga_config=GAConfig(seed=1, population_size=10, generations=10))
    decision = lb.select(force_ga=True)
    assert decision is not None
    assert decision["selected_server"] in {"vm1", "vm2", "vm3"}
    assert "next_hop_ip" in decision and decision["next_hop_ip"].startswith("10.0.0.")


def test_unhealthy_servers_skipped():
    pool = _pool()
    pool.update_metrics("vm3", healthy=False)
    lb = HybridLoadBalancer(pool, ga_interval_seconds=0.0)
    seen = set()
    for _ in range(5):
        d = lb.select(force_ga=True)
        if d:
            seen.add(d["selected_server"])
    assert "vm3" not in seen
