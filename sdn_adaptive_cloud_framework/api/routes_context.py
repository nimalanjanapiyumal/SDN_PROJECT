"""Context update endpoints: monitoring + ML-prediction inputs."""
from __future__ import annotations

from fastapi import APIRouter
from dataclasses import asdict

from ..controller import get_state
from .schemas import ContextRequest, MlPredictionRequest


router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("/update")
def update_context(payload: ContextRequest) -> dict:
    """Receive monitoring/threat/SLA context that DFPS will apply to ranking."""
    state = get_state()
    ctx = state.update_context(payload.model_dump(exclude_none=True))
    return {"context": asdict(ctx)}


@router.get("/current")
def current_context() -> dict:
    state = get_state()
    return {"context": asdict(state.context), "last_ml_prediction": state.last_ml_prediction}


@router.post("/ml-prediction")
def receive_ml_prediction(payload: MlPredictionRequest) -> dict:
    """Receive an ML prediction (risk level, recommended action) from the ML module."""
    state = get_state()
    state.set_ml_prediction(payload.model_dump(exclude_none=True))
    return {"accepted": True, "stored": state.last_ml_prediction}
