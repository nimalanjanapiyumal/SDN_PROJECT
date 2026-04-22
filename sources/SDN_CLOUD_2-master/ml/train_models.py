from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))


import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from ml.common import CLASS_LABELS, FEATURE_NAMES
from ml.data_generator import generate_dataset


def load_or_create_dataset(dataset_path: Path, samples_per_class: int, seed: int) -> pd.DataFrame:
    if dataset_path.exists():
        return pd.read_csv(dataset_path)
    dataset = generate_dataset(samples_per_class=samples_per_class, seed=seed)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(dataset_path, index=False)
    return dataset


def train_models(dataset: pd.DataFrame, seed: int = 42) -> Dict[str, object]:
    X = dataset[FEATURE_NAMES]
    y_cls = dataset["label"]
    y_reg = dataset["sla_risk_score"]

    X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
        X,
        y_cls,
        y_reg,
        test_size=0.25,
        random_state=seed,
        stratify=y_cls,
    )

    classifier = RandomForestClassifier(
        n_estimators=250,
        random_state=seed,
        class_weight="balanced",
        min_samples_leaf=2,
    )
    regressor = RandomForestRegressor(
        n_estimators=250,
        random_state=seed,
        min_samples_leaf=2,
    )

    classifier.fit(X_train, y_cls_train)
    regressor.fit(X_train, y_reg_train)

    cls_pred = classifier.predict(X_test)
    reg_pred = regressor.predict(X_test)

    report = {
        "classifier_accuracy": float(accuracy_score(y_cls_test, cls_pred)),
        "classifier_report": classification_report(y_cls_test, cls_pred, output_dict=True),
        "classifier_confusion_matrix": confusion_matrix(y_cls_test, cls_pred, labels=CLASS_LABELS).tolist(),
        "regression_mae": float(mean_absolute_error(y_reg_test, reg_pred)),
        "regression_r2": float(r2_score(y_reg_test, reg_pred)),
        "feature_names": FEATURE_NAMES,
        "class_labels": CLASS_LABELS,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }

    return {
        "classifier": classifier,
        "regressor": regressor,
        "report": report,
    }


def save_artifacts(artifacts: Dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": artifacts["classifier"],
            "feature_names": FEATURE_NAMES,
            "class_labels": CLASS_LABELS,
        },
        output_dir / "classifier.joblib",
    )
    joblib.dump(
        {
            "model": artifacts["regressor"],
            "feature_names": FEATURE_NAMES,
        },
        output_dir / "sla_regressor.joblib",
    )
    (output_dir / "training_report.json").write_text(
        json.dumps(artifacts["report"], indent=2)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SDN anomaly and SLA-risk models.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/synthetic_sdn_dataset.csv"),
        help="CSV dataset path. Generated if it does not exist.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ml/models"),
        help="Directory where trained models will be stored.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1500,
        help="Samples per class when a dataset must be generated.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_or_create_dataset(args.dataset, samples_per_class=args.samples, seed=args.seed)
    artifacts = train_models(dataset, seed=args.seed)
    save_artifacts(artifacts, args.output_dir)

    report = artifacts["report"]
    print("Training complete")
    print(f"Dataset rows: {len(dataset)}")
    print(f"Classifier accuracy: {report['classifier_accuracy']:.4f}")
    print(f"Regression MAE: {report['regression_mae']:.4f}")
    print(f"Regression R2: {report['regression_r2']:.4f}")
    print(f"Saved models to: {args.output_dir}")


if __name__ == "__main__":
    main()
