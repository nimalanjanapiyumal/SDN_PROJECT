from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))


import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from ml.common import CLASS_LABELS, FEATURE_NAMES, clamp


def _normal_samples(n: int, rng: np.random.Generator) -> pd.DataFrame:
    data = {
        "active_flows": rng.integers(15, 90, size=n),
        "packet_rate_per_sec": rng.uniform(600, 3500, size=n),
        "byte_rate_per_sec": rng.uniform(0.8e6, 8.5e6, size=n),
        "max_link_utilization_ratio": rng.uniform(0.12, 0.55, size=n),
        "controller_cpu_percent": rng.uniform(8, 35, size=n),
        "controller_memory_percent": rng.uniform(16, 42, size=n),
        "packet_in_rate_per_sec": rng.uniform(1, 12, size=n),
    }
    frame = pd.DataFrame(data)
    frame["label"] = "normal"
    return frame


def _congestion_samples(n: int, rng: np.random.Generator) -> pd.DataFrame:
    data = {
        "active_flows": rng.integers(50, 180, size=n),
        "packet_rate_per_sec": rng.uniform(2500, 9000, size=n),
        "byte_rate_per_sec": rng.uniform(9e6, 28e6, size=n),
        "max_link_utilization_ratio": rng.uniform(0.72, 1.0, size=n),
        "controller_cpu_percent": rng.uniform(25, 60, size=n),
        "controller_memory_percent": rng.uniform(20, 52, size=n),
        "packet_in_rate_per_sec": rng.uniform(4, 24, size=n),
    }
    frame = pd.DataFrame(data)
    frame["label"] = "congestion"
    return frame


def _ddos_samples(n: int, rng: np.random.Generator) -> pd.DataFrame:
    data = {
        "active_flows": rng.integers(120, 650, size=n),
        "packet_rate_per_sec": rng.uniform(12000, 85000, size=n),
        "byte_rate_per_sec": rng.uniform(3e6, 18e6, size=n),
        "max_link_utilization_ratio": rng.uniform(0.68, 1.0, size=n),
        "controller_cpu_percent": rng.uniform(45, 96, size=n),
        "controller_memory_percent": rng.uniform(24, 64, size=n),
        "packet_in_rate_per_sec": rng.uniform(80, 320, size=n),
    }
    frame = pd.DataFrame(data)
    frame["label"] = "ddos"
    return frame


def _port_scan_samples(n: int, rng: np.random.Generator) -> pd.DataFrame:
    data = {
        "active_flows": rng.integers(90, 520, size=n),
        "packet_rate_per_sec": rng.uniform(1800, 14000, size=n),
        "byte_rate_per_sec": rng.uniform(1.5e5, 3.5e6, size=n),
        "max_link_utilization_ratio": rng.uniform(0.08, 0.55, size=n),
        "controller_cpu_percent": rng.uniform(18, 65, size=n),
        "controller_memory_percent": rng.uniform(18, 48, size=n),
        "packet_in_rate_per_sec": rng.uniform(120, 520, size=n),
    }
    frame = pd.DataFrame(data)
    frame["label"] = "port_scan"
    return frame


def add_sla_risk(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    class_weight = frame["label"].map(
        {
            "normal": 0.05,
            "congestion": 0.35,
            "ddos": 0.55,
            "port_scan": 0.45,
        }
    )
    risk = (
        0.32 * frame["max_link_utilization_ratio"]
        + 0.22 * (frame["controller_cpu_percent"] / 100.0)
        + 0.14 * (frame["controller_memory_percent"] / 100.0)
        + 0.18 * np.clip(frame["packet_in_rate_per_sec"] / 300.0, 0, 1.5)
        + 0.14 * np.clip(frame["active_flows"] / 500.0, 0, 1.5)
        + class_weight
        + rng.normal(0.0, 0.03, size=len(frame))
    )
    frame["sla_risk_score"] = risk.apply(lambda x: clamp(float(x), 0.0, 1.0))
    return frame


def generate_dataset(samples_per_class: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = [
        _normal_samples(samples_per_class, rng),
        _congestion_samples(samples_per_class, rng),
        _ddos_samples(samples_per_class, rng),
        _port_scan_samples(samples_per_class, rng),
    ]
    dataset = pd.concat(frames, ignore_index=True)
    dataset = add_sla_risk(dataset, rng)
    dataset = dataset.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return dataset


def save_dataset(path: Path, samples_per_class: int = 1500, seed: int = 42) -> pd.DataFrame:
    frame = generate_dataset(samples_per_class=samples_per_class, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic SDN training data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic_sdn_dataset.csv"),
        help="Path to the generated CSV file.",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=1500,
        help="Number of samples generated for each traffic class.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = save_dataset(args.output, samples_per_class=args.samples_per_class, seed=args.seed)
    counts = frame["label"].value_counts().to_dict()
    print(f"Saved dataset to {args.output}")
    print(f"Rows: {len(frame)}")
    print(f"Class distribution: {counts}")


if __name__ == "__main__":
    main()
