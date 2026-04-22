
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

FEATURE_NAMES: List[str] = [
    "active_flows",
    "packet_rate_per_sec",
    "byte_rate_per_sec",
    "max_link_utilization_ratio",
    "controller_cpu_percent",
    "controller_memory_percent",
    "packet_in_rate_per_sec",
]

CLASS_LABELS: List[str] = ["normal", "congestion", "ddos", "port_scan"]


@dataclass
class FeatureVector:
    active_flows: float
    packet_rate_per_sec: float
    byte_rate_per_sec: float
    max_link_utilization_ratio: float
    controller_cpu_percent: float
    controller_memory_percent: float
    packet_in_rate_per_sec: float

    def to_numpy(self) -> np.ndarray:
        return np.array(
            [
                self.active_flows,
                self.packet_rate_per_sec,
                self.byte_rate_per_sec,
                self.max_link_utilization_ratio,
                self.controller_cpu_percent,
                self.controller_memory_percent,
                self.packet_in_rate_per_sec,
            ],
            dtype=float,
        )


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def vector_from_metrics(metrics: Dict[str, float]) -> np.ndarray:
    values = [
        float(metrics.get("active_flows", 0.0)),
        float(metrics.get("packet_rate_per_sec", 0.0)),
        float(metrics.get("byte_rate_per_sec", 0.0)),
        float(metrics.get("max_link_utilization_ratio", 0.0)),
        float(metrics.get("controller_cpu_percent", 0.0)),
        float(metrics.get("controller_memory_percent", 0.0)),
        float(metrics.get("packet_in_rate_per_sec", 0.0)),
    ]
    return np.array(values, dtype=float).reshape(1, -1)


def metrics_template() -> Dict[str, float]:
    return {
        "active_flows": 0.0,
        "packet_rate_per_sec": 0.0,
        "byte_rate_per_sec": 0.0,
        "max_link_utilization_ratio": 0.0,
        "controller_cpu_percent": 0.0,
        "controller_memory_percent": 0.0,
        "packet_in_rate_per_sec": 0.0,
    }


def class_index_to_label(index: int) -> str:
    return CLASS_LABELS[int(index)]


def one_hot_prediction(label: str) -> Dict[str, int]:
    return {name: int(name == label) for name in CLASS_LABELS}
