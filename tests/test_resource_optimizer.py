from sdn_hybrid_lb.utils.config import load_config
from adaptive_cloud_platform.services.resource_optimizer_service import ResourceOptimizerService


def test_optimizer_builds_weight_plan():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    plan = service.build_plan()
    assert plan['source'] == 'optimizer'
    assert isinstance(plan['backend_weights'], dict)
    assert plan['backend_weights']


def test_component_one_routes_and_records_flow_rule():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    result = service.route_request(
        client_ip='10.0.0.1',
        client_port=41001,
        vip_port=8000,
        ip_proto=6,
        request_size_kb=64,
        priority=100,
    )
    assert result['accepted'] is True
    assert result['flow_rule']['action'] == 'set_dst_and_forward'
    assert service.component_status()['metrics']['rr_decisions'] == 1


def test_component_one_fault_tolerance_excludes_unhealthy_backend():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    service.set_backend_health('web-1', False, 'test fault')
    for index in range(6):
        result = service.route_request(
            client_ip='10.0.0.1',
            client_port=42000 + index,
            vip_port=8000,
            ip_proto=6,
        )
        assert result['accepted'] is True
        assert result['backend']['name'] != 'web-1'


def test_component_one_metric_update_feeds_ga_plan():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    updated = service.update_backend_metrics(
        'web-1',
        cpu_percent=92,
        memory_percent=87,
        bandwidth_percent=75,
        latency_ms=180,
    )
    assert updated['updated'] is True
    plan = service.build_plan()
    assert 'web-1' in plan['backend_weights']


def test_component_two_context_triggers_automatic_component_one_plan():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    allocation = service.apply_context_feedback({
        'source': 'ml',
        'max_link_utilization_ratio': 0.91,
        'latency_ms': 210,
        'packet_in_rate_per_sec': 900,
        'recommendation': 'reroute_top_talker',
    })
    assert allocation['triggered'] is True
    assert allocation['plan']['backend_weights']


def test_component_four_security_action_faults_matching_backend():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    allocation = service.apply_security_feedback({
        'action': 'quarantine',
        'subject': '10.0.0.7',
        'reason': 'test backend compromise',
    })
    assert allocation['triggered'] is True
    assert allocation['backend'] == 'web-1'
    assert service.lb._get_backend('web-1').healthy is False


def test_component_three_load_balance_intent_routes_automatically():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    allocation = service.apply_intent_feedback({
        'type': 'load_balance',
        'src_ip': '10.0.0.2',
        'dst_port': 8000,
        'priority': 5,
        'metadata': {'request_size_kb': 64},
    })
    assert allocation['triggered'] is True
    assert allocation['route_result']['accepted'] is True
