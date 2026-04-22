from __future__ import annotations

from typing import Dict, Any


class MLService:
    """Lightweight rule-based fallback policy service.

    The repository already includes the original ML training and policy-agent code under `src/ml/`.
    This service is the always-available integrated runtime layer that can work even when trained
    model artifacts are not yet present.
    """

    def infer(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        congestion = float(metrics.get('max_link_utilization_ratio', 0.0) or 0.0)
        packet_in = float(metrics.get('packet_in_rate_per_sec', 0.0) or 0.0)
        latency = float(metrics.get('latency_ms', 0.0) or 0.0)

        if packet_in > 500 or congestion > 0.90:
            label = 'ddos'
            recommendation = 'block_highest_risk_source'
            confidence = 0.90
        elif congestion > 0.70 or latency > 150:
            label = 'congestion'
            recommendation = 'reroute_top_talker'
            confidence = 0.78
        else:
            label = 'normal'
            recommendation = 'observe'
            confidence = 0.65

        return {
            'source': 'ml',
            'label': label,
            'recommendation': recommendation,
            'confidence': confidence,
        }
