from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentRequest(BaseModel):
    type: str = Field(default="generic")
    intent: Optional[str] = None
    priority: int = 1
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    proto: Optional[str] = None
    dst_port: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextUpdate(BaseModel):
    source: str = "monitoring"
    threat: Optional[str] = None
    congestion: Optional[str] = None
    load: Optional[str] = None
    latency_ms: Optional[float] = None
    packet_rate_per_sec: Optional[float] = None
    byte_rate_per_sec: Optional[float] = None
    max_link_utilization_ratio: Optional[float] = None
    controller_cpu_percent: Optional[float] = None
    controller_memory_percent: Optional[float] = None
    packet_in_rate_per_sec: Optional[float] = None
    recommendation: Optional[str] = None
    confidence: Optional[float] = None


class ResourcePlanRequest(BaseModel):
    source: str = "optimizer"
    plan_version: str = "1.0.0"
    backend_weights: Dict[str, float]
    reason: Optional[str] = None


class SecurityActionRequest(BaseModel):
    source: str = "security"
    action: str
    subject: str
    severity: int = 3
    reason: Optional[str] = None


class PolicyEnforcementRequest(BaseModel):
    type: str
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    duration: Optional[int] = 60
    reason: Optional[str] = None


class SessionLoginRequest(BaseModel):
    user_id: str
    ip: str
    password: str


class SessionVerifyRequest(BaseModel):
    token: str
    ip: str
    bytes_sent: int = 0
