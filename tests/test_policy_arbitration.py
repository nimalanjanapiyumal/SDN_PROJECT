from adaptive_cloud_platform.state import IntegratedState
from adaptive_cloud_platform.adapters.execution_adapter import ExecutionAdapter
from adaptive_cloud_platform.services.orchestrator_service import OrchestratorService


def test_security_overrides_manual_and_plan():
    state = IntegratedState()
    orchestrator = OrchestratorService(state, ExecutionAdapter())
    orchestrator.record_resource_plan({'source': 'optimizer', 'backend_weights': {'a': 0.6}})
    orchestrator.record_intent({'type': 'load_balance', 'priority': 3})
    orchestrator.record_security_action({'source': 'security', 'action': 'quarantine', 'subject': '10.0.0.2', 'severity': 5})
    decision = orchestrator.decide()
    assert decision is not None
    assert decision['source'] == 'security'
    assert decision['decision_type'] == 'quarantine'
