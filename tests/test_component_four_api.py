from adaptive_cloud_platform.app import (
    component_four_auth_login,
    component_four_auth_verify,
    component_four_block_indicator,
    component_four_enforce_segmentation,
    component_four_evaluate_flow,
)
from adaptive_cloud_platform.models import (
    ComponentFourCtiBlockRequest,
    ComponentFourFlowEvaluationRequest,
    SessionLoginRequest,
    SessionVerifyRequest,
)
import json


def test_component_four_auth_endpoints_trigger_quarantine():
    login = component_four_auth_login(SessionLoginRequest(user_id="admin", ip="10.0.0.2", password="admin123"))
    assert login["authenticated"] is True

    result = component_four_auth_verify(SessionVerifyRequest(
        token=login["token"],
        ip="10.0.0.99",
        bytes_sent=130 * 1024 * 1024,
    ))

    assert result["allowed"] is False
    assert result["security_action"]["action"] == "quarantine"
    assert result["component_4_enforcement"]["accepted"] is True
    json.dumps(result)


def test_component_four_segmentation_endpoint_enforces_and_blocks_lateral_flow():
    enforced = component_four_enforce_segmentation()
    assert enforced["enforced"] is True
    assert enforced["count"] >= 2

    result = component_four_evaluate_flow(ComponentFourFlowEvaluationRequest(
        src_ip="10.0.0.1",
        dst_ip="10.0.0.12",
        dst_port=3306,
        protocol="tcp",
    ))

    assert result["allowed"] is False
    assert result["component_4_enforcement"]["accepted"] is True


def test_component_four_cti_block_endpoint_integrates_security_action():
    result = component_four_block_indicator(ComponentFourCtiBlockRequest(
        value="198.51.100.1",
        reason="test indicator",
    ))

    assert result["blocked"] is True
    assert result["security_action"]["action"] == "block"
    assert result["component_4_enforcement"]["accepted"] is True
