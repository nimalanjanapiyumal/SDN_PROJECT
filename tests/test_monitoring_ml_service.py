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
