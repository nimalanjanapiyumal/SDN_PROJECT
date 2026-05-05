"""REST routes for user intents (Module 1 / outline section 'Main APIs')."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..controller import IntentValidationError, get_state
from .schemas import IntentRequest, IntentResponse


router = APIRouter(prefix="/api/intent", tags=["intent"])


@router.post("/submit", response_model=IntentResponse, status_code=status.HTTP_201_CREATED)
def submit_intent(payload: IntentRequest) -> IntentResponse:
    """Validate, rank, translate and install a user intent."""
    state = get_state()
    try:
        result = state.submit_intent(payload.model_dump(exclude_none=True))
    except IntentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IntentResponse(**result)


@router.get("/list")
def list_intents() -> dict:
    state = get_state()
    return {"intents": [i.to_dict() for i in state.list_intents()]}


@router.delete("/{intent_id}")
def remove_intent(intent_id: str) -> dict:
    state = get_state()
    removed = state.remove_intent(intent_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"intent {intent_id} not found")
    return {"removed": [r.to_dict() for r in removed]}
