
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vm-a1-controller'))

from sdn_hybrid_lb.algorithms.hybrid import HybridLoadBalancer
from sdn_hybrid_lb.utils.config import AppConfig


def make_cfg():
    return AppConfig.from_dict({
        'controller': {'flow_idle_timeout': 30, 'ga_interval_sec': 9999, 'poll_interval_sec': 2},
        'hybrid': {
            'rr': {'mode': 'round_robin'},
            'overload_threshold': {'cpu': 0.9, 'mem': 0.9, 'bw': 0.9, 'conn': 0.8},
            'ga': {'fitness': {'util_weights': {'cpu': 0.4, 'mem': 0.3, 'bw': 0.2, 'conn': 0.1}}},
        },
        'vip': {'ip': '10.0.0.100', 'mac': '00:00:00:00:00:64'},
        'backends': [
            {'name': 'srv1', 'ip': '10.0.0.2', 'mac': '00:00:00:00:00:02', 'dpid': 1, 'port': 2, 'capacity': {'cpu_cores': 2, 'mem_gb': 2, 'bw_mbps': 100, 'max_connections': 10}},
            {'name': 'srv2', 'ip': '10.0.0.3', 'mac': '00:00:00:00:00:03', 'dpid': 1, 'port': 3, 'capacity': {'cpu_cores': 2, 'mem_gb': 2, 'bw_mbps': 100, 'max_connections': 100}},
        ],
    })


def test_status_contains_backends():
    lb = HybridLoadBalancer(make_cfg())
    status = lb.status()
    assert status['vip']['ip'] == '10.0.0.100'
    assert len(status['backends']) == 2


def test_capacity_based_overload_check():
    lb = HybridLoadBalancer(make_cfg())
    srv1 = lb._get_backend('srv1')
    srv2 = lb._get_backend('srv2')
    srv1.metrics.active_connections = 8
    srv2.metrics.active_connections = 8
    assert lb._is_eligible(srv2) is True
    assert lb._is_eligible(srv1) is False
