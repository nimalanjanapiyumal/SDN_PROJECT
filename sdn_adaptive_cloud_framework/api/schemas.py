"""Pydantic request/response models for the REST API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- /api/intent ----

class IntentRequest(BaseModel):
    intent_type: str = Field(..., description="security|load_balancing|monitoring|segmentation|optimization")
    action: str = Field(..., description="block|allow|reroute|quarantine|balance|monitor|segment")
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    protocol: Optional[str] = Field(None, description="tcp|udp|icmp")
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    src_segment: Optional[str] = None
    dst_segment: Optional[str] = None
    next_hop_ip: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    intent_id: Optional[str] = None


class IntentResponse(BaseModel):
    intent: Dict[str, Any]
    translated: Dict[str, Any]
    ranking: Dict[str, Any]
    records: List[Dict[str, Any]]


# ---- /api/context ----

class ContextRequest(BaseModel):
    threat: Optional[str] = "low"
    congestion: Optional[str] = "low"
    sla_risk: Optional[str] = "low"
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class MlPredictionRequest(BaseModel):
    prediction: str
    risk_level: str = "low"
    recommended_action: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)


# ---- /api/flow ----

class FlowInstallRequest(BaseModel):
    match: Dict[str, Any]
    flow_action: str = Field(..., description="drop|forward")
    priority: int = 100
    dpid: Optional[int] = None
    out_port: Optional[int] = None
    intent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FlowDeleteRequest(BaseModel):
    rule_id: Optional[str] = None
    intent_id: Optional[str] = None
