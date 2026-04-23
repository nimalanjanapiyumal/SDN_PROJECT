from adaptive_cloud_platform.services.intent_controller_service import IntentControllerService
from adaptive_cloud_platform.state import IntegratedState


def test_component_three_translates_video_intent_to_qos_rule():
    service = IntentControllerService(IntegratedState())

    result = service.submit_intent({
        "intent": "Prioritize video streaming during peak hours",
        "priority": 8,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.7",
        "proto": "tcp",
        "dst_port": 443,
        "expected_type": "qos",
    })

    assert result["classification"]["type"] == "qos"
    assert result["rules"][0]["semantic_action"] == "prioritize_latency_sensitive_flow"
    assert result["rules"][0]["match"]["tcp_dst"] == 443
    assert result["rules"][0]["openflow_compatible"] is True


def test_component_three_context_update_reoptimizes_existing_rules():
    service = IntentControllerService(IntegratedState())
    service.submit_intent({
        "intent": "Balance traffic across available servers",
        "priority": 7,
        "src_ip": "10.0.0.3",
        "dst_ip": "10.0.0.7",
        "proto": "tcp",
        "dst_port": 8000,
    })

    update = service.update_context({
        "threat": "low",
        "congestion": "high",
        "load": "overloaded",
        "latency_ms": 180,
        "bandwidth_utilization": 0.88,
        "resource_utilization": 0.82,
        "time_context": "peak_hours",
        "policy_context": "sla",
    })

    assert update["adapted_intents"] == 1
    assert update["adapted_rules"] == 1
    assert service.status()["metrics"]["context_updates"] == 1
    assert service.status()["metrics"]["active_rules"] >= 1


def test_component_three_security_intent_generates_drop_rule():
    service = IntentControllerService(IntegratedState())

    result = service.submit_intent({
        "intent": "Block suspicious traffic from 10.0.0.50",
        "priority": 10,
        "src_ip": "10.0.0.50",
        "dst_ip": "10.0.0.12",
        "proto": "tcp",
        "dst_port": 22,
    })

    rule = result["rules"][0]
    assert result["classification"]["type"] == "security"
    assert rule["actions"] == [{"type": "DROP"}]
    assert rule["priority"] > 32000
