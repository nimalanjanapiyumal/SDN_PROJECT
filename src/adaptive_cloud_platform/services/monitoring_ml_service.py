from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional
import importlib.util
import json
import shutil
import time

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from adaptive_cloud_platform.services.ml_service import MLService
from ml.common import CLASS_LABELS, FEATURE_NAMES, vector_from_metrics


class MonitoringMLService:
    """Component 2 runtime layer for monitoring, prediction, visualization, and feedback."""

    def __init__(self, fallback: MLService, model_dir: str = "ml/models") -> None:
        self.fallback = fallback
        self.model_dir = Path(model_dir)
        self.classifier_path = self.model_dir / "classifier.joblib"
        self.regressor_path = self.model_dir / "sla_regressor.joblib"
        self.report_path = self.model_dir / "training_report.json"
        self.telemetry: List[Dict[str, Any]] = []
        self.predictions: List[Dict[str, Any]] = []
        self.policy_results: List[Dict[str, Any]] = []
        self._classifier: Any = None
        self._regressor: Any = None
        self._load_models()

    def predict(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.normalize_metrics(metrics)
        if self._classifier is not None and self._regressor is not None:
            vector = vector_from_metrics(normalized)
            label = str(self._classifier.predict(vector)[0])
            confidence = 0.0
            if hasattr(self._classifier, "predict_proba"):
                probabilities = self._classifier.predict_proba(vector)[0]
                classes = list(self._classifier.classes_)
                confidence = float(probabilities[classes.index(label)]) if label in classes else float(max(probabilities))
            risk = float(self._regressor.predict(vector)[0])
            model_source = "trained_random_forest"
        else:
            fallback = self._rule_based_prediction(normalized)
            label = fallback["label"]
            confidence = fallback["confidence"]
            risk = fallback["sla_risk_score"]
            model_source = "rule_based_fallback"

        risk = max(0.0, min(1.0, risk))
        prediction = {
            "source": "ml",
            "label": label,
            "recommendation": self._recommendation_for(label, risk),
            "confidence": round(float(confidence), 4),
            "sla_risk_score": round(float(risk), 4),
            "model_source": model_source,
            "ts": time.time(),
        }
        self.predictions.append(prediction)
        self.predictions = self.predictions[-100:]
        return prediction

    def normalize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        return {
            "active_flows": float(metrics.get("active_flows", 0.0) or 0.0),
            "packet_rate_per_sec": float(metrics.get("packet_rate_per_sec", 0.0) or 0.0),
            "byte_rate_per_sec": float(metrics.get("byte_rate_per_sec", 0.0) or 0.0),
            "max_link_utilization_ratio": float(metrics.get("max_link_utilization_ratio", 0.0) or 0.0),
            "controller_cpu_percent": float(metrics.get("controller_cpu_percent", 0.0) or 0.0),
            "controller_memory_percent": float(metrics.get("controller_memory_percent", 0.0) or 0.0),
            "packet_in_rate_per_sec": float(metrics.get("packet_in_rate_per_sec", 0.0) or 0.0),
        }

    def record_observation(
        self,
        context: Dict[str, Any],
        prediction: Dict[str, Any],
        policy_result: Optional[Dict[str, Any]] = None,
        mitigation_latency_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        observed_label = context.get("observed_label")
        row = {
            **self.normalize_metrics(context),
            "observed_label": observed_label,
            "prediction": prediction,
            "policy_result": policy_result or {},
            "mitigation_latency_ms": mitigation_latency_ms,
            "ts": time.time(),
        }
        self.telemetry.append(row)
        self.telemetry = self.telemetry[-200:]
        if policy_result:
            self.policy_results.append({
                "prediction_label": prediction.get("label"),
                "recommendation": prediction.get("recommendation"),
                "triggered": bool(policy_result.get("allocation", {}).get("triggered")),
                "mitigation_latency_ms": mitigation_latency_ms,
                "ts": time.time(),
            })
            self.policy_results = self.policy_results[-100:]
        return row

    def train_models(self, samples_per_class: int = 600, seed: int = 42) -> Dict[str, Any]:
        dataset = self._synthetic_dataset(samples_per_class=samples_per_class, seed=seed)
        x = dataset["features"]
        y_cls = dataset["labels"]
        y_reg = dataset["risks"]
        x_train, x_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
            x,
            y_cls,
            y_reg,
            test_size=0.25,
            random_state=seed,
            stratify=y_cls,
        )
        classifier = RandomForestClassifier(
            n_estimators=160,
            random_state=seed,
            class_weight="balanced",
            min_samples_leaf=2,
        )
        regressor = RandomForestRegressor(
            n_estimators=160,
            random_state=seed,
            min_samples_leaf=2,
        )
        classifier.fit(x_train, y_cls_train)
        regressor.fit(x_train, y_reg_train)
        cls_pred = classifier.predict(x_test)
        reg_pred = regressor.predict(x_test)
        report = {
            "classifier_accuracy": float(accuracy_score(y_cls_test, cls_pred)),
            "regression_mae": float(mean_absolute_error(y_reg_test, reg_pred)),
            "regression_r2": float(r2_score(y_reg_test, reg_pred)),
            "feature_names": FEATURE_NAMES,
            "class_labels": CLASS_LABELS,
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "samples_per_class": int(samples_per_class),
            "seed": int(seed),
            "trained_at": time.time(),
        }
        self.model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": classifier, "feature_names": FEATURE_NAMES, "class_labels": CLASS_LABELS}, self.classifier_path)
        joblib.dump({"model": regressor, "feature_names": FEATURE_NAMES}, self.regressor_path)
        self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._classifier = classifier
        self._regressor = regressor
        return report

    def scenario_metrics(self, scenario: str) -> Dict[str, float]:
        scenarios = {
            "normal": {
                "active_flows": 45,
                "packet_rate_per_sec": 2200,
                "byte_rate_per_sec": 4_500_000,
                "max_link_utilization_ratio": 0.34,
                "controller_cpu_percent": 24,
                "controller_memory_percent": 32,
                "packet_in_rate_per_sec": 6,
            },
            "congestion": {
                "active_flows": 150,
                "packet_rate_per_sec": 7800,
                "byte_rate_per_sec": 24_000_000,
                "max_link_utilization_ratio": 0.86,
                "controller_cpu_percent": 56,
                "controller_memory_percent": 48,
                "packet_in_rate_per_sec": 22,
            },
            "ddos": {
                "active_flows": 520,
                "packet_rate_per_sec": 42_000,
                "byte_rate_per_sec": 14_000_000,
                "max_link_utilization_ratio": 0.94,
                "controller_cpu_percent": 88,
                "controller_memory_percent": 58,
                "packet_in_rate_per_sec": 210,
            },
            "port_scan": {
                "active_flows": 320,
                "packet_rate_per_sec": 9200,
                "byte_rate_per_sec": 1_200_000,
                "max_link_utilization_ratio": 0.42,
                "controller_cpu_percent": 46,
                "controller_memory_percent": 36,
                "packet_in_rate_per_sec": 340,
            },
        }
        return scenarios.get(scenario, scenarios["normal"])

    def status(self) -> Dict[str, Any]:
        labeled = [row for row in self.telemetry if row.get("observed_label")]
        correct = [
            row for row in labeled
            if row["prediction"].get("label") == row.get("observed_label")
        ]
        latencies = [
            float(row["mitigation_latency_ms"])
            for row in self.policy_results
            if row.get("mitigation_latency_ms") is not None
        ]
        avg_latency = round(mean(latencies), 2) if latencies else None
        baseline_latency = 250.0
        latency_improvement = None
        if avg_latency is not None and baseline_latency > 0:
            latency_improvement = round(((baseline_latency - avg_latency) / baseline_latency) * 100.0, 2)
        latest_prediction = self.predictions[-1] if self.predictions else None
        latest_label = (latest_prediction or {}).get("label")
        latest_recommendation = (latest_prediction or {}).get("recommendation")
        return {
            "component": {
                "number": 2,
                "name": "Monitoring, Visualization, and ML-Based Optimization",
                "features": [
                    "telemetry ingestion for latency, throughput, CPU, memory, flows, and packet-in rate",
                    "ML anomaly/congestion/security-risk prediction",
                    "automatic policy feedback into the integrated SDN decision loop",
                    "Prometheus and Grafana provisioning assets",
                    "evaluation metrics for prediction accuracy, mitigation latency, and SLA risk",
                ],
            },
            "models": self.model_status(),
            "metrics": {
                "telemetry_points": len(self.telemetry),
                "predictions": len(self.predictions),
                "labeled_points": len(labeled),
                "prediction_accuracy_percent": round((len(correct) / len(labeled) * 100.0), 2) if labeled else None,
                "avg_mitigation_latency_ms": avg_latency,
                "reactive_baseline_latency_ms": baseline_latency,
                "latency_improvement_percent": latency_improvement,
                "high_risk_predictions": sum(1 for item in self.predictions if float(item.get("sla_risk_score", 0.0)) >= 0.65),
                "policy_feedback_events": len(self.policy_results),
            },
            "expected_outcomes": {
                "real_time_monitoring_and_visualization": {
                    "title": "Real-time monitoring and visualization",
                    "implemented": True,
                    "status": "active" if self.telemetry else "ready",
                    "metric": len(self.telemetry),
                    "metric_label": "telemetry points",
                    "detail": "Prometheus-ready telemetry, Grafana dashboards, and live Component 2 runtime views are wired into the platform.",
                },
                "ml_based_anomaly_prediction_and_preemptive_traffic_management": {
                    "title": "ML anomaly prediction and preemptive traffic management",
                    "implemented": True,
                    "status": "active" if latest_prediction else "ready",
                    "metric": len(self.predictions),
                    "metric_label": "predictions",
                    "detail": f"Latest inference routes to {latest_recommendation or 'observe'} using the {latest_label or 'pending'} risk label.",
                },
                "faster_response_times_and_higher_sla_compliance": {
                    "title": "Faster response times and SLA support",
                    "implemented": True,
                    "status": "measured" if avg_latency is not None else "ready",
                    "metric": avg_latency,
                    "metric_label": "avg mitigation ms",
                    "detail": (
                        f"Average mitigation latency is {avg_latency} ms against a {baseline_latency:.0f} ms reactive baseline "
                        f"({latency_improvement}% improvement)."
                        if avg_latency is not None and latency_improvement is not None
                        else "Mitigation latency will be measured after live monitoring and policy feedback cycles run."
                    ),
                },
                "decision_making_feedback_loop": {
                    "title": "Continuous decision-making loop",
                    "implemented": True,
                    "status": "active" if self.policy_results else "ready",
                    "metric": len(self.policy_results),
                    "metric_label": "feedback events",
                    "detail": "Monitoring events feed ML predictions, then push policy updates into Components 1, 3, and 4 for adaptive enforcement.",
                },
            },
            "latest_prediction": latest_prediction,
            "latest_telemetry": self.telemetry[-1] if self.telemetry else None,
            "recent_predictions": self.predictions[-20:],
            "recent_policy_results": self.policy_results[-20:],
            "platform": self.platform_status(),
        }

    def model_status(self) -> Dict[str, Any]:
        report = None
        if self.report_path.exists():
            try:
                report = json.loads(self.report_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                report = None
        return {
            "classifier_path": str(self.classifier_path),
            "regressor_path": str(self.regressor_path),
            "classifier_exists": self.classifier_path.exists(),
            "regressor_exists": self.regressor_path.exists(),
            "loaded": self._classifier is not None and self._regressor is not None,
            "training_report": report,
        }

    def platform_status(self) -> Dict[str, Any]:
        prometheus_config = Path("monitoring/prometheus/prometheus.yml")
        grafana_dashboard = Path("monitoring/grafana/dashboards/overview.json")
        docker_compose = Path("docker-compose.yml")
        tensorflow_installed = importlib.util.find_spec("tensorflow") is not None
        pytorch_installed = importlib.util.find_spec("torch") is not None
        sklearn_installed = importlib.util.find_spec("sklearn") is not None
        local_tools = {
            "prometheus": shutil.which("prometheus"),
            "grafana_server": shutil.which("grafana-server"),
            "docker": shutil.which("docker"),
            "ryu_manager": shutil.which("ryu-manager"),
            "mininet_mn": shutil.which("mn"),
        }
        prometheus_installed = bool(local_tools["prometheus"])
        grafana_installed = bool(local_tools["grafana_server"])
        prometheus_defined = prometheus_config.exists() and docker_compose.exists()
        grafana_defined = grafana_dashboard.exists() and docker_compose.exists()
        return {
            "prometheus_config": {
                "path": str(prometheus_config),
                "exists": prometheus_config.exists(),
            },
            "grafana_dashboard": {
                "path": str(grafana_dashboard),
                "exists": grafana_dashboard.exists(),
            },
            "docker_compose": docker_compose.exists(),
            "local_tools": local_tools,
            "monitoring_endpoints": [
                {
                    "name": "Integrated Console",
                    "url": "http://127.0.0.1:8080/",
                    "category": "console",
                    "status": "live",
                },
                {
                    "name": "Component 2 Status API",
                    "url": "http://127.0.0.1:8080/api/v1/component-2/status",
                    "category": "api",
                    "status": "live",
                },
                {
                    "name": "OpenAPI Docs",
                    "url": "http://127.0.0.1:8080/docs",
                    "category": "api",
                    "status": "interactive",
                },
                {
                    "name": "Metrics Exporter",
                    "url": "http://127.0.0.1:9108/metrics",
                    "category": "metrics",
                    "status": "local exporter",
                },
                {
                    "name": "Prometheus Server",
                    "url": "http://127.0.0.1:9090/",
                    "category": "monitoring",
                    "status": "installed" if prometheus_installed else ("files ready" if prometheus_defined else "not installed"),
                },
                {
                    "name": "Grafana Server",
                    "url": "http://127.0.0.1:3000/",
                    "category": "dashboard",
                    "status": "installed" if grafana_installed else ("files ready" if grafana_defined else "not installed"),
                },
            ],
            "software_tools": [
                {
                    "name": "Mininet",
                    "purpose": "Network Simulation",
                    "docs_url": "https://mininet.org/walkthrough",
                    "installed": bool(local_tools["mininet_mn"]),
                    "runtime": "Linux or WSL runtime",
                },
                {
                    "name": "Ryu Controller",
                    "purpose": "SDN Programming",
                    "docs_url": "https://book.ryu-sdn.org/en/",
                    "installed": bool(local_tools["ryu_manager"]),
                    "runtime": "Linux or WSL runtime",
                },
                {
                    "name": "Prometheus",
                    "purpose": "Monitoring",
                    "docs_url": "https://prometheus.io/docs/introduction/overview/",
                    "installed": prometheus_installed,
                    "configured": prometheus_defined,
                    "runtime": "Local web server at :9090",
                },
                {
                    "name": "Grafana",
                    "purpose": "Visualization",
                    "docs_url": "https://grafana.com/docs/grafana/latest/",
                    "installed": grafana_installed,
                    "configured": grafana_defined,
                    "runtime": "Local web server at :3000",
                },
                {
                    "name": "TensorFlow",
                    "purpose": "ML Models",
                    "docs_url": "https://www.tensorflow.org/learn",
                    "installed": tensorflow_installed,
                    "runtime": "Python package",
                },
                {
                    "name": "PyTorch",
                    "purpose": "ML Models",
                    "docs_url": "https://pytorch.org/docs/stable/index.html",
                    "installed": pytorch_installed,
                    "runtime": "Python package",
                },
                {
                    "name": "Scikit-learn",
                    "purpose": "ML Models",
                    "docs_url": "https://scikit-learn.org/stable/user_guide.html",
                    "installed": sklearn_installed,
                    "runtime": "Python package",
                },
            ],
            "hardware_requirements": {
                "cpu": "8-core recommended",
                "memory": "16 GB RAM recommended",
                "storage": "500 GB SSD recommended",
            },
            "mode": "integrated_api_runtime_with_prometheus_grafana_assets",
        }

    def _load_models(self) -> None:
        if not (self.classifier_path.exists() and self.regressor_path.exists()):
            return
        self._classifier = joblib.load(self.classifier_path)["model"]
        self._regressor = joblib.load(self.regressor_path)["model"]

    def _rule_based_prediction(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        fallback = self.fallback.infer(metrics)
        packet_in = metrics["packet_in_rate_per_sec"]
        link_util = metrics["max_link_utilization_ratio"]
        packet_rate = metrics["packet_rate_per_sec"]
        controller_cpu = metrics["controller_cpu_percent"]
        if packet_in > 140 and link_util < 0.65:
            label = "port_scan"
            confidence = 0.84
            risk = 0.74
        elif packet_rate > 15_000 or (packet_in > 80 and link_util >= 0.65):
            label = "ddos"
            confidence = 0.9
            risk = 0.86
        elif link_util > 0.70 or controller_cpu > 70:
            label = "congestion"
            confidence = 0.79
            risk = 0.66
        else:
            label = fallback["label"]
            confidence = fallback["confidence"]
            risk = 0.18 if label == "normal" else 0.55
        return {"label": label, "confidence": confidence, "sla_risk_score": risk}

    def _recommendation_for(self, label: str, risk: float) -> str:
        if label == "ddos":
            return "block_highest_risk_source"
        if label == "port_scan":
            return "rate_limit_scanner"
        if label == "congestion" or risk >= 0.65:
            return "reroute_top_talker"
        return "observe"

    def _synthetic_dataset(self, samples_per_class: int, seed: int) -> Dict[str, np.ndarray]:
        rng = np.random.default_rng(seed)
        rows: List[List[float]] = []
        labels: List[str] = []
        risks: List[float] = []
        ranges = {
            "normal": [(15, 90), (600, 3500), (0.8e6, 8.5e6), (0.12, 0.55), (8, 35), (16, 42), (1, 12), (0.02, 0.22)],
            "congestion": [(50, 180), (2500, 9000), (9e6, 28e6), (0.72, 1.0), (25, 60), (20, 52), (4, 24), (0.42, 0.76)],
            "ddos": [(120, 650), (12000, 85000), (3e6, 18e6), (0.68, 1.0), (45, 96), (24, 64), (80, 320), (0.62, 0.98)],
            "port_scan": [(90, 520), (1800, 14000), (1.5e5, 3.5e6), (0.08, 0.55), (18, 65), (18, 48), (120, 520), (0.45, 0.88)],
        }
        for label in CLASS_LABELS:
            spec = ranges[label]
            for _ in range(samples_per_class):
                values = [float(rng.uniform(low, high)) for low, high in spec[:7]]
                risk = float(rng.uniform(*spec[7]))
                rows.append(values)
                labels.append(label)
                risks.append(risk)
        return {
            "features": np.array(rows, dtype=float),
            "labels": np.array(labels, dtype=object),
            "risks": np.array(risks, dtype=float),
        }
