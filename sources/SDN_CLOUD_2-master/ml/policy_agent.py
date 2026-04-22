from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))


import argparse
import json
import logging
import math
import signal
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import joblib
import requests
from prometheus_client import Counter, Gauge, start_http_server

from ml.common import CLASS_LABELS, one_hot_prediction, vector_from_metrics

LOGGER = logging.getLogger("policy-agent")


class PolicyAgent:
    def __init__(
        self,
        prometheus_url: str,
        controller_url: str,
        classifier_path: Path,
        regressor_path: Path,
        poll_interval: int = 5,
        metrics_port: int = 9102,
        risk_threshold: float = 0.55,
        score_threshold: float = 0.65,
    ) -> None:
        self.prometheus_url = prometheus_url.rstrip("/")
        self.controller_url = controller_url.rstrip("/")
        self.classifier_bundle = joblib.load(classifier_path)
        self.regressor_bundle = joblib.load(regressor_path)
        self.classifier = self.classifier_bundle["model"]
        self.regressor = self.regressor_bundle["model"]
        self.poll_interval = poll_interval
        self.risk_threshold = risk_threshold
        self.score_threshold = score_threshold
        self.session = requests.Session()
        self.stop_requested = False
        self.cooldowns: Dict[str, float] = {}

        start_http_server(metrics_port, addr="0.0.0.0")
        self.prediction_score_metric = Gauge(
            "cloud_sdn_prediction_score",
            "Latest ML prediction confidence score.",
        )
        self.sla_risk_metric = Gauge(
            "cloud_sdn_sla_risk_score",
            "Latest SLA-risk score estimated by the ML model.",
        )
        self.class_metric = Gauge(
            "cloud_sdn_prediction_class",
            "One-hot encoded predicted traffic class.",
            ["label"],
        )
        self.policy_actions_total = Counter(
            "cloud_sdn_policy_actions_total",
            "Total number of actions requested by the policy agent.",
            ["action"],
        )
        self.last_inference_epoch = Gauge(
            "cloud_sdn_last_inference_epoch",
            "Unix epoch time of the latest inference.",
        )

    def query_prometheus(self, expr: str) -> float:
        endpoint = f"{self.prometheus_url}/api/v1/query"
        response = self.session.get(endpoint, params={"query": expr}, timeout=4)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {payload}")
        result = payload.get("data", {}).get("result", [])
        if not result:
            return 0.0
        return float(result[0]["value"][1])

    def get_live_metrics(self) -> Dict[str, float]:
        queries = {
            "active_flows": "sum(cloud_sdn_active_flows)",
            "packet_rate_per_sec": "sum(cloud_sdn_packet_rate_per_sec)",
            "byte_rate_per_sec": "sum(cloud_sdn_byte_rate_per_sec)",
            "max_link_utilization_ratio": "max(cloud_sdn_link_utilization_ratio)",
            "controller_cpu_percent": "cloud_sdn_controller_cpu_percent",
            "controller_memory_percent": "cloud_sdn_controller_memory_percent",
            "packet_in_rate_per_sec": "cloud_sdn_packet_in_rate_per_sec",
        }
        metrics = {}
        for key, expr in queries.items():
            metrics[key] = self.query_prometheus(expr)
        return metrics

    def get_controller_state(self) -> Dict[str, object]:
        response = self.session.get(f"{self.controller_url}/api/v1/state", timeout=4)
        response.raise_for_status()
        return response.json()

    def fallback_metrics_from_state(self, state: Dict[str, object]) -> Dict[str, float]:
        summary = state.get("summary", {}) if isinstance(state, dict) else {}
        return {
            "active_flows": float(summary.get("active_flows", 0.0)),
            "packet_rate_per_sec": float(summary.get("packet_rate_per_sec", 0.0)),
            "byte_rate_per_sec": float(summary.get("byte_rate_per_sec", 0.0)),
            "max_link_utilization_ratio": float(summary.get("max_link_utilization_ratio", 0.0)),
            "controller_cpu_percent": float(summary.get("controller_cpu_percent", 0.0)),
            "controller_memory_percent": float(summary.get("controller_memory_percent", 0.0)),
            "packet_in_rate_per_sec": float(summary.get("packet_in_rate_per_sec", 0.0)),
        }

    def infer(self, metrics: Dict[str, float]) -> Tuple[str, float, float]:
        vector = vector_from_metrics(metrics)
        label = str(self.classifier.predict(vector)[0])
        probability = 0.0
        if hasattr(self.classifier, "predict_proba"):
            probs = self.classifier.predict_proba(vector)[0]
            classes = list(self.classifier.classes_)
            if label in classes:
                probability = float(probs[classes.index(label)])
            else:
                probability = float(max(probs))
        risk = float(self.regressor.predict(vector)[0])
        risk = max(0.0, min(1.0, risk))
        return label, probability, risk

    def _should_throttle_action(self, key: str, cooldown_seconds: int = 30) -> bool:
        now = time.time()
        expires = self.cooldowns.get(key, 0.0)
        if expires > now:
            return True
        self.cooldowns[key] = now + cooldown_seconds
        return False

    def apply_policy(self, label: str, score: float, risk: float, state: Dict[str, object]) -> Optional[Dict[str, object]]:
        top_talkers = state.get("top_talkers", []) if isinstance(state, dict) else []
        talker = top_talkers[0] if top_talkers else {}
        src_ip = talker.get("src_ip")
        dst_ip = talker.get("dst_ip")
        actions = []
        payload = None

        if label in {"ddos", "port_scan"} and score >= self.score_threshold and src_ip:
            key = f"block:{src_ip}"
            if not self._should_throttle_action(key):
                payload = {
                    "type": "block",
                    "src_ip": src_ip,
                    "duration": 90,
                    "reason": f"ML predicted {label}",
                    "score": score,
                    "risk": risk,
                }
                actions.append("block")
        elif label == "congestion" and risk >= self.risk_threshold and src_ip and dst_ip:
            key = f"reroute:{src_ip}:{dst_ip}"
            if not self._should_throttle_action(key):
                payload = {
                    "type": "reroute",
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "duration": 90,
                    "reason": "Predicted congestion",
                    "score": score,
                    "risk": risk,
                }
                actions.append("reroute")
        elif label == "normal":
            mitigations = state.get("mitigations", [])
            if mitigations:
                first = mitigations[0]
                src_ip = first.get("src_ip")
                if src_ip:
                    key = f"clear:{src_ip}"
                    if not self._should_throttle_action(key, cooldown_seconds=20):
                        payload = {
                            "type": "clear",
                            "src_ip": src_ip,
                            "reason": "State returned to normal",
                            "score": score,
                            "risk": risk,
                        }
                        actions.append("clear")

        if payload:
            response = self.session.post(
                f"{self.controller_url}/api/v1/policy/enforce",
                json=payload,
                timeout=4,
            )
            response.raise_for_status()
            for action in actions:
                self.policy_actions_total.labels(action=action).inc()
            return response.json()
        return None

    def update_metrics(self, label: str, score: float, risk: float) -> None:
        self.prediction_score_metric.set(score)
        self.sla_risk_metric.set(risk)
        self.last_inference_epoch.set(time.time())
        hot = one_hot_prediction(label)
        for class_label, value in hot.items():
            self.class_metric.labels(label=class_label).set(value)

    def run_once(self) -> Dict[str, object]:
        state: Dict[str, object]
        try:
            metrics = self.get_live_metrics()
            state = self.get_controller_state()
        except Exception as exc:  # pragma: no cover - fallback path
            LOGGER.warning("Prometheus/controller fetch failed, using controller-state fallback: %s", exc)
            state = self.get_controller_state()
            metrics = self.fallback_metrics_from_state(state)

        label, score, risk = self.infer(metrics)
        self.update_metrics(label, score, risk)
        result = {
            "metrics": metrics,
            "prediction": {"label": label, "score": score, "risk": risk},
            "policy_result": self.apply_policy(label, score, risk, state),
        }
        return result

    def serve_forever(self) -> None:
        LOGGER.info("Policy agent started")
        while not self.stop_requested:
            try:
                result = self.run_once()
                LOGGER.info("Inference result: %s", json.dumps(result, default=str))
            except Exception as exc:  # pragma: no cover - runtime protection
                LOGGER.exception("Policy loop iteration failed: %s", exc)
            time.sleep(self.poll_interval)

    def request_stop(self, *_args: object) -> None:
        self.stop_requested = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDN adaptive ML policy agent")
    parser.add_argument(
        "--prometheus-url",
        default="http://127.0.0.1:9090",
        help="Prometheus base URL.",
    )
    parser.add_argument(
        "--controller-url",
        default="http://127.0.0.1:8080",
        help="Controller REST base URL.",
    )
    parser.add_argument(
        "--classifier-path",
        type=Path,
        default=Path("ml/models/classifier.joblib"),
        help="Path to the trained classifier bundle.",
    )
    parser.add_argument(
        "--regressor-path",
        type=Path,
        default=Path("ml/models/sla_regressor.joblib"),
        help="Path to the trained regressor bundle.",
    )
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds.")
    parser.add_argument("--metrics-port", type=int, default=9102, help="Prometheus exporter port.")
    parser.add_argument("--risk-threshold", type=float, default=0.55, help="SLA risk threshold.")
    parser.add_argument("--score-threshold", type=float, default=0.65, help="Prediction confidence threshold.")
    parser.add_argument("--once", action="store_true", help="Run one inference cycle and exit.")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    agent = PolicyAgent(
        prometheus_url=args.prometheus_url,
        controller_url=args.controller_url,
        classifier_path=args.classifier_path,
        regressor_path=args.regressor_path,
        poll_interval=args.poll_interval,
        metrics_port=args.metrics_port,
        risk_threshold=args.risk_threshold,
        score_threshold=args.score_threshold,
    )

    signal.signal(signal.SIGINT, agent.request_stop)
    signal.signal(signal.SIGTERM, agent.request_stop)

    if args.once:
        result = agent.run_once()
        print(json.dumps(result, indent=2))
        return

    agent.serve_forever()


if __name__ == "__main__":
    main()
