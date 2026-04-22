from pathlib import Path

import joblib

from ml.common import CLASS_LABELS, FEATURE_NAMES, vector_from_metrics


def test_vector_from_metrics_shape():
    vector = vector_from_metrics(
        {
            "active_flows": 55,
            "packet_rate_per_sec": 3200,
            "byte_rate_per_sec": 6_000_000,
            "max_link_utilization_ratio": 0.45,
            "controller_cpu_percent": 22,
            "controller_memory_percent": 28,
            "packet_in_rate_per_sec": 4.5,
        }
    )
    assert vector.shape == (1, len(FEATURE_NAMES))


def test_trained_classifier_files_exist():
    assert Path("ml/models/classifier.joblib").exists()
    assert Path("ml/models/sla_regressor.joblib").exists()


def test_classifier_predicts_known_label():
    classifier_bundle = joblib.load("ml/models/classifier.joblib")
    model = classifier_bundle["model"]
    vector = vector_from_metrics(
        {
            "active_flows": 250,
            "packet_rate_per_sec": 28000,
            "byte_rate_per_sec": 9_500_000,
            "max_link_utilization_ratio": 0.85,
            "controller_cpu_percent": 78,
            "controller_memory_percent": 33,
            "packet_in_rate_per_sec": 180,
        }
    )
    label = model.predict(vector)[0]
    assert label in CLASS_LABELS
