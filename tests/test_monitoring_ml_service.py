from adaptive_cloud_platform.services.ml_service import MLService
from adaptive_cloud_platform.services.monitoring_ml_service import MonitoringMLService


def test_component_two_predicts_ddos_scenario():
    service = MonitoringMLService(MLService())
    metrics = service.scenario_metrics("ddos")
    prediction = service.predict(metrics)
    assert prediction["label"] in {"ddos", "port_scan", "congestion"}
    assert prediction["sla_risk_score"] >= 0.5


def test_component_two_records_observation_accuracy():
    service = MonitoringMLService(MLService())
    metrics = service.scenario_metrics("normal")
    prediction = service.predict(metrics)
    context = {**metrics, "observed_label": prediction["label"]}
    service.record_observation(context, prediction, policy_result={"allocation": {"triggered": False}})
    status = service.status()
    assert status["metrics"]["telemetry_points"] == 1
    assert status["metrics"]["prediction_accuracy_percent"] == 100.0


def test_component_two_status_exposes_outcomes_and_platform_links():
    service = MonitoringMLService(MLService())
    status = service.status()
    platform = status["platform"]

    assert status["expected_outcomes"]["real_time_monitoring_and_visualization"]["implemented"] is True
    assert status["expected_outcomes"]["decision_making_feedback_loop"]["implemented"] is True
    assert any(item["name"] == "Prometheus Server" for item in platform["monitoring_endpoints"])
    assert any(tool["name"] == "Grafana" for tool in platform["software_tools"])
    assert any(
        tool["name"] == "Scikit-learn" and tool["docs_url"].startswith("https://")
        for tool in platform["software_tools"]
    )
