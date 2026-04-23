from adaptive_cloud_platform.app import component_three_context, component_three_intent
from adaptive_cloud_platform.models import ComponentThreeContextUpdate, ComponentThreeIntentRequest


def test_component_three_intent_endpoint_integrates_policy_loop():
    body = component_three_intent(ComponentThreeIntentRequest(**{
        "intent": "Balance traffic across available servers",
        "priority": 7,
        "src_ip": "10.0.0.3",
        "dst_ip": "10.0.0.7",
        "proto": "tcp",
        "dst_port": 8000,
        "expected_type": "load_balance",
    }))

    assert body["accepted"] is True
    assert body["component_3_translation"]["classification"]["type"] == "load_balance"
    assert body["component_3_translation"]["rules"][0]["openflow_compatible"] is True
    assert body["component_1_allocation"]["triggered"] is True


def test_component_three_qos_intent_endpoint_accepts_non_routing_intent():
    body = component_three_intent(ComponentThreeIntentRequest(**{
        "intent": "Prioritize video streaming during peak hours",
        "priority": 8,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.7",
        "proto": "tcp",
        "dst_port": 443,
        "expected_type": "qos",
    }))

    assert body["accepted"] is True
    assert body["component_3_translation"]["classification"]["type"] == "qos"
    assert body["component_1_allocation"]["route_result"] is None


def test_component_three_context_endpoint_adapts_rules():
    body = component_three_context(ComponentThreeContextUpdate(**{
        "threat": "elevated",
        "congestion": "high",
        "load": "high",
        "latency_ms": 160,
        "bandwidth_utilization": 0.81,
        "resource_utilization": 0.74,
        "time_context": "peak_hours",
        "policy_context": "sla",
    }))

    assert body["accepted"] is True
    assert body["component_3_context"]["adapted_rules"] >= 1
    assert "component_1_allocation" in body
