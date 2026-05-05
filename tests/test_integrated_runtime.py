import time
from pathlib import Path

import pytest

from adaptive_cloud_platform.app import (
    app,
    auth_logout,
    auth_verify_otp,
    auth_status,
    automation_start,
    automation_status,
    automation_stop,
    integrated_run,
    integrated_status,
    monitoring_start,
    openstack_deploy,
    openstack_start,
    openstack_status,
    openstack_stop,
    platform_validate,
    sdn_start,
    sdn_status,
    operator_auth_service,
)
from adaptive_cloud_platform.models import (
    IntegratedAutomationRequest,
    IntegratedRunRequest,
    MonitoringStackRequest,
    OpenStackControlRequest,
    OperatorOtpVerifyRequest,
    SdnLabStartRequest,
)


def _login_with_otp(client) -> str:
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    payload = login.json()
    assert payload["otp_required"] is True
    verify = client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": payload["challenge_id"],
            "otp_code": operator_auth_service.current_otp_code_for_testing(),
        },
    )
    assert verify.status_code == 200
    verified = verify.json()
    assert verified["authenticated"] is True
    return verified["token"]


def test_integrated_run_chains_all_components():
    result = integrated_run(IntegratedRunRequest(scenario="mixed", reset=True, workload_requests=8))

    assert result["ran"] is True
    assert result["scenario"] == "mixed"
    assert {step["component"] for step in result["steps"]} == {1, 2, 3, 4}
    assert result["summary"]["operator_health"]["automatic_pipeline_ready"] is True


def test_integrated_status_reports_readiness_and_run_history():
    status = integrated_status()

    assert status["operator_health"]["components_modelled"] == 4
    assert "component_1" in status
    assert "component_4" in status
    assert status["integrated_runs"]["count"] >= 1
    assert status["readiness"]["monitoring"]["files_ready"] is True


def test_platform_validation_includes_sdn_and_observability_assets():
    validation = platform_validate()

    assert validation["observability"]["files"]["prometheus_config"]["exists"] is True
    assert validation["observability"]["files"]["grafana_dashboard"]["exists"] is True
    assert validation["sdn_lab"]["files"]["integrated_ryu_app"]["exists"] is True
    assert validation["sdn_lab"]["files"]["runbook"]["exists"] is True
    assert "runtime" in validation


def test_sdn_runtime_reports_topology_and_openflow():
    status = sdn_status()

    assert "topology" in status
    assert "openflow" in status
    assert "commands" in status
    assert "views" in status
    assert "openstack" in status
    assert "controller_window" in status["lab"]


def test_sdn_start_and_monitoring_start_return_runtime_payloads():
    sdn_result = sdn_start(SdnLabStartRequest(scenario="mixed", duration_sec=60, interactive=False, link_mode="basic"))
    monitoring_result = monitoring_start(MonitoringStackRequest())

    assert "runtime" in sdn_result
    assert "action" in sdn_result
    assert "runtime" in monitoring_result
    assert "action" in monitoring_result


def test_openstack_controls_return_runtime_payloads():
    deploy_result = openstack_deploy(OpenStackControlRequest(deployment_mode="auto"))
    start_result = openstack_start(OpenStackControlRequest(deployment_mode="auto"))
    stop_result = openstack_stop(OpenStackControlRequest(deployment_mode="auto"))
    status = openstack_status()

    assert "runtime" in deploy_result
    assert "action" in deploy_result
    assert "runtime" in start_result
    assert "action" in start_result
    assert "runtime" in stop_result
    assert "action" in stop_result
    assert "mode" in status
    assert "inventory" in status


def test_operator_auth_login_status_and_logout():
    result = operator_auth_service.login("admin", "admin123")
    assert result["authenticated"] is False
    assert result["otp_required"] is True

    verified = auth_verify_otp(OperatorOtpVerifyRequest(
        challenge_id=result["challenge_id"],
        otp_code=operator_auth_service.current_otp_code_for_testing(),
    ))
    assert verified["authenticated"] is True
    token = verified["token"]
    assert auth_status(token)["authenticated"] is True
    assert auth_logout(token)["logged_out"] is True


def test_http_operator_auth_required_for_sdn_start():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    client = TestClient(app)

    unauthorized = client.post("/api/v1/sdn/start", json={
        "scenario": "mixed",
        "duration_sec": 60,
        "interactive": False,
        "link_mode": "basic",
        "start_monitoring": False,
    })
    assert unauthorized.status_code == 401

    token = _login_with_otp(client)

    authorized = client.post(
        "/api/v1/sdn/start",
        headers={"X-Operator-Token": token},
        json={
            "scenario": "mixed",
            "duration_sec": 60,
            "interactive": False,
            "link_mode": "basic",
            "start_monitoring": False,
        },
    )
    assert authorized.status_code == 200
    assert "action" in authorized.json()


def test_http_bearer_auth_and_optional_control_bodies():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    client = TestClient(app)
    token = _login_with_otp(client)
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get("/api/v1/auth/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["authenticated"] is True

    monitoring = client.post("/api/v1/monitoring/start", headers=headers)
    assert monitoring.status_code == 200

    openstack = client.post("/api/v1/openstack/start", headers=headers)
    assert openstack.status_code == 200
    assert "action" in openstack.json()

    sdn = client.post("/api/v1/sdn/start", headers=headers)
    assert sdn.status_code == 200
    assert "runtime" in sdn.json()

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["logged_out"] is True


def test_sdn_event_ingest_updates_runtime_status():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post("/api/v1/sdn/events", json={
        "event_type": "attack_blocked",
        "source": "test",
        "severity": "critical",
        "message": "Synthetic DDoS was blocked",
        "metadata": {"attack_type": "DDoS", "src_ip": "10.0.0.3", "blocked": True},
    })
    assert response.status_code == 200
    status = client.get("/api/v1/sdn/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["topology"]["alerts"]
    assert payload["lab"]["controller_window"]["recent_attacks"]


def test_sdn_lab_files_are_packaged():
    assert Path("src/sitecustomize.py").exists()
    assert Path("src/adaptive_cloud_platform/sdn/ryu_integrated_app.py").exists()
    assert Path("scripts/run_integrated_sdn_lab.sh").exists()
    assert Path("scripts/control_openstack.sh").exists()
    assert Path("docs/RYU_MININET_RUNBOOK.md").exists()


def test_system_automation_can_start_and_stop():
    automation_stop()
    started = automation_start(IntegratedAutomationRequest(
        strategy='cycle',
        preferred_scenario='normal',
        scenario_sequence=['normal'],
        interval_sec=1.0,
        workload_requests=4,
        max_cycles=1,
        reset_on_start=True,
    ))

    time.sleep(0.15)
    status = automation_status()
    assert started['preferred_scenario'] == 'normal'
    assert status['executed_cycles'] >= 1
    assert status['last_result'] is not None
    stopped = automation_stop()
    assert stopped['running'] is False
