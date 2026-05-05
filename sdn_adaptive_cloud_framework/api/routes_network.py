"""Network views: discovered hosts, topology, and direct flow control."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..controller import get_state
from .schemas import FlowDeleteRequest, FlowInstallRequest


router = APIRouter(prefix="/api", tags=["network"])


@router.get("/network/hosts")
def list_hosts() -> dict:
    state = get_state()
    return {"hosts": state.hosts.to_list_dict()}


@router.get("/network/topology")
def topology() -> dict:
    state = get_state()
    return state.topology.to_dict()


@router.post("/flow/install")
def install_flow(payload: FlowInstallRequest) -> dict:
    if payload.flow_action not in {"drop", "forward"}:
        raise HTTPException(400, "flow_action must be 'drop' or 'forward'")
    state = get_state()
    records = state.flow_manager.install(
        match=payload.match,
        flow_action=payload.flow_action,
        priority=payload.priority,
        intent_id=payload.intent_id,
        dpid=payload.dpid,
        out_port=payload.out_port,
        metadata=payload.metadata,
    )
    return {"records": [r.to_dict() for r in records]}


@router.post("/flow/delete")
def delete_flow(payload: FlowDeleteRequest) -> dict:
    state = get_state()
    if payload.rule_id:
        rec = state.flow_manager.remove_by_rule_id(payload.rule_id)
        if rec is None:
            raise HTTPException(404, f"rule_id {payload.rule_id} not found")
        return {"removed": [rec.to_dict()]}
    if payload.intent_id:
        records = state.flow_manager.remove_by_intent(payload.intent_id)
        if not records:
            raise HTTPException(404, f"no flows for intent {payload.intent_id}")
        return {"removed": [r.to_dict() for r in records]}
    raise HTTPException(400, "either rule_id or intent_id is required")


@router.get("/flow/list")
def list_flows() -> dict:
    state = get_state()
    return {"flows": [r.to_dict() for r in state.flow_manager.list_records()]}
