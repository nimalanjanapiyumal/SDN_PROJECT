import time
from pathlib import Path

from adaptive_cloud_platform.app import (
    automation_start,
    automation_status,
    automation_stop,
    integrated_run,
    integrated_status,
    monitoring_start,
    platform_validate,
    sdn_start,
    sdn_status,
)
from adaptive_cloud_platform.models import IntegratedAutomationRequest, IntegratedRunRequest, MonitoringStackRequest, SdnLabStartRequest


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


def test_sdn_start_and_monitoring_start_return_runtime_payloads():
    sdn_result = sdn_start(SdnLabStartRequest(scenario="mixed", duration_sec=60, interactive=False, link_mode="basic"))
    monitoring_result = monitoring_start(MonitoringStackRequest())

    assert "runtime" in sdn_result
    assert "action" in sdn_result
    assert "runtime" in monitoring_result
    assert "action" in monitoring_result


def test_sdn_lab_files_are_packaged():
    assert Path("src/adaptive_cloud_platform/sdn/ryu_integrated_app.py").exists()
    assert Path("scripts/run_integrated_sdn_lab.sh").exists()
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
