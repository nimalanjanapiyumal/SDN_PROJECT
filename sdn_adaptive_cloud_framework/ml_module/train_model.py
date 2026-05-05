"""Train the baseline classifier from a CSV dataset (Module 6)."""
from __future__ import annotations

import argparse
import os
from typing import List

import joblib
import numpy as np


FEATURES = [
    "latency_ms", "throughput_mbps", "packet_loss",
    "cpu_usage", "memory_usage", "flow_count",
]


def _load_csv(path: str):
    import csv
    X: List[List[float]] = []
    y: List[str] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append([float(row[f]) for f in FEATURES])
            y.append(row["label"])
    return np.array(X), np.array(y)


def train_and_save(csv_path: str, model_out: str) -> str:
    """Train a Random Forest classifier and persist it via joblib.

    Returns the saved model path. ``csv_path`` must contain the columns
    listed in ``FEATURES`` plus a ``label`` column ("normal", "congestion",
    "anomaly", ...).
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    X, y = _load_csv(csv_path)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    print(classification_report(y_test, clf.predict(X_test)))

    os.makedirs(os.path.dirname(model_out) or ".", exist_ok=True)
    joblib.dump(clf, model_out)
    return model_out


def _cli() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Train SDN ML classifier")
    parser.add_argument("--csv", required=True, help="Path to labelled CSV dataset")
    parser.add_argument("--out", default="ml_module/model.pkl", help="Output model path")
    args = parser.parse_args()
    train_and_save(args.csv, args.out)


if __name__ == "__main__":  # pragma: no cover
    _cli()


__all__ = ["FEATURES", "train_and_save"]
