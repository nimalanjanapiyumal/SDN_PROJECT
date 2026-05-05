"""Lightweight prediction layer (Module 6).

Wraps a trained classifier and exposes a tiny FastAPI app on its own port so
the SDN controller can ``POST /api/ml/predict`` to get a risk classification.
The default model is a thresholded heuristic — it lets the rest of the
framework run end-to-end before a real model is trained, and is replaced by
``train_model.train_and_save`` once a dataset is available.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import joblib
    _JOBLIB_AVAILABLE = True
except Exception:  # pragma: no cover
    joblib = None  # type: ignore[assignment]
    _JOBLIB_AVAILABLE = False

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    _FASTAPI_AVAILABLE = True
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment, misc]
    _FASTAPI_AVAILABLE = False


@dataclass
class HeuristicModel:
    """Fallback model used when no trained pickle is available."""

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        latency = float(features.get("latency_ms", 0))
        loss = float(features.get("packet_loss", 0))
        cpu = float(features.get("cpu_usage", 0))
        flows = float(features.get("flow_count", 0))

        score = (latency / 200.0) + (loss / 5.0) + (cpu / 100.0) + (flows / 1000.0)
        if score > 1.5:
            return {
                "prediction": "congestion_risk",
                "risk_level": "high",
                "recommended_action": "reroute_traffic",
                "score": round(score, 3),
            }
        if score > 0.8:
            return {
                "prediction": "elevated_load",
                "risk_level": "medium",
                "recommended_action": "rebalance",
                "score": round(score, 3),
            }
        return {
            "prediction": "normal",
            "risk_level": "low",
            "recommended_action": "none",
            "score": round(score, 3),
        }


def load_model(path: Optional[str] = None) -> Any:
    path = path or os.environ.get("SDN_ML_MODEL")
    if path and os.path.exists(path) and _JOBLIB_AVAILABLE:
        try:
            return joblib.load(path)
        except Exception:
            pass
    return HeuristicModel()


if _FASTAPI_AVAILABLE:

    class PredictRequest(BaseModel):
        latency_ms: float = 0.0
        throughput_mbps: float = 0.0
        packet_loss: float = 0.0
        cpu_usage: float = 0.0
        memory_usage: float = 0.0
        flow_count: float = 0.0

    def create_app() -> FastAPI:
        app = FastAPI(title="SDN ML Prediction", version="0.1.0")
        model = load_model()

        @app.get("/healthz")
        def healthz() -> dict:
            return {"status": "ok", "model": type(model).__name__}

        @app.post("/api/ml/predict")
        def predict(req: PredictRequest) -> dict:
            features = req.model_dump()
            if hasattr(model, "predict_proba"):  # sklearn-style
                import numpy as np
                vec = np.array([list(features.values())])
                pred = model.predict(vec)[0]
                proba = float(np.max(model.predict_proba(vec)))
                return {
                    "prediction": str(pred),
                    "risk_level": "high" if proba > 0.8 else "medium" if proba > 0.5 else "low",
                    "score": proba,
                    "features": features,
                }
            return {**model.predict(features), "features": features}

        return app

    app = create_app()
else:  # pragma: no cover
    app = None  # type: ignore[assignment]


__all__ = ["HeuristicModel", "load_model", "app"]
