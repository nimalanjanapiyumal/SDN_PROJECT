from sdn_hybrid_lb.utils.config import load_config
from adaptive_cloud_platform.services.resource_optimizer_service import ResourceOptimizerService


def test_optimizer_builds_weight_plan():
    cfg = load_config('configs/system.yaml')
    service = ResourceOptimizerService(cfg)
    plan = service.build_plan()
    assert plan['source'] == 'optimizer'
    assert isinstance(plan['backend_weights'], dict)
    assert plan['backend_weights']
