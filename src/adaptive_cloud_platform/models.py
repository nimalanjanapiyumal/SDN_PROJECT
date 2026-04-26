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
    expected_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextUpdate(BaseModel):
    source: str = "monitoring"
    active_flows: Optional[float] = None
    threat: Optional[str] = None
    congestion: Optional[str] = None
    load: Optional[str] = None
    latency_ms: Optional[float] = None
    bandwidth_utilization: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    resource_utilization: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    time_context: Optional[str] = None
    policy_context: Optional[str] = None
    packet_rate_per_sec: Optional[float] = None
    byte_rate_per_sec: Optional[float] = None
    max_link_utilization_ratio: Optional[float] = None
    controller_cpu_percent: Optional[float] = None
    controller_memory_percent: Optional[float] = None
    packet_in_rate_per_sec: Optional[float] = None
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    label: Optional[str] = None
    observed_label: Optional[str] = None
    sla_risk_score: Optional[float] = None
    top_talker_src_ip: Optional[str] = None
    top_talker_dst_ip: Optional[str] = None


class ResourcePlanRequest(BaseModel):
    source: str = "optimizer"
    plan_version: str = "1.0.0"
    backend_weights: Dict[str, float]
    reason: Optional[str] = None


class ComponentOneRouteRequest(BaseModel):
    client_ip: str = "10.0.0.1"
    client_port: int = Field(default=40000, ge=1, le=65535)
    vip_port: int = Field(default=8000, ge=1, le=65535)
    ip_proto: int = Field(default=6, ge=1, le=255)
    request_size_kb: float = Field(default=128.0, ge=0.0)
    priority: int = Field(default=100, ge=1, le=65535)


class ComponentOneBackendMetricUpdate(BaseModel):
    cpu_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    memory_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    bandwidth_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    active_connections: Optional[int] = Field(default=None, ge=0)
    latency_ms: Optional[float] = Field(default=None, ge=0.0)
    throughput_mbps: Optional[float] = Field(default=None, ge=0.0)


class ComponentOneBackendHealthUpdate(BaseModel):
    healthy: bool = True
    reason: Optional[str] = None


class ComponentOnePortStatsUpdate(BaseModel):
    dpid: int = Field(ge=1)
    port: int = Field(ge=1)
    tx_bytes: int = Field(ge=0)
    rx_bytes: int = Field(ge=0)


class ComponentOneWorkloadSimulationRequest(BaseModel):
    requests: int = Field(default=24, ge=1, le=500)
    clients: List[str] = Field(default_factory=lambda: ["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    start_port: int = Field(default=41000, ge=1, le=65535)
    vip_port: int = Field(default=8000, ge=1, le=65535)
    request_size_kb: float = Field(default=128.0, ge=0.0)
    recompute_after: bool = True
    inject_fault_backend: Optional[str] = None


class ComponentTwoTelemetryRequest(BaseModel):
    source: str = "component-2-monitoring"
    active_flows: float = Field(default=45.0, ge=0.0)
    packet_rate_per_sec: float = Field(default=2200.0, ge=0.0)
    byte_rate_per_sec: float = Field(default=4_500_000.0, ge=0.0)
    max_link_utilization_ratio: float = Field(default=0.34, ge=0.0, le=1.0)
    controller_cpu_percent: float = Field(default=24.0, ge=0.0, le=100.0)
    controller_memory_percent: float = Field(default=32.0, ge=0.0, le=100.0)
    packet_in_rate_per_sec: float = Field(default=6.0, ge=0.0)
    latency_ms: Optional[float] = Field(default=None, ge=0.0)
    observed_label: Optional[str] = None
    top_talker_src_ip: Optional[str] = None
    top_talker_dst_ip: Optional[str] = None


class ComponentTwoTrainingRequest(BaseModel):
    samples_per_class: int = Field(default=600, ge=50, le=5000)
    seed: int = 42


class ComponentThreeIntentRequest(BaseModel):
    type: str = Field(default="generic")
    intent: str = Field(default="Prioritize video streaming during peak hours")
    priority: int = Field(default=6, ge=1, le=10)
    src_ip: Optional[str] = "10.0.0.1"
    dst_ip: Optional[str] = "10.0.0.7"
    proto: Optional[str] = "tcp"
    dst_port: Optional[int] = Field(default=443, ge=1, le=65535)
    expected_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComponentThreeContextUpdate(BaseModel):
    source: str = "component-3-context"
    threat: Optional[str] = "low"
    congestion: Optional[str] = "low"
    load: Optional[str] = "normal"
    latency_ms: Optional[float] = Field(default=35.0, ge=0.0)
    bandwidth_utilization: Optional[float] = Field(default=0.25, ge=0.0, le=1.0)
    resource_utilization: Optional[float] = Field(default=0.32, ge=0.0, le=1.0)
    time_context: Optional[str] = "business_hours"
    policy_context: Optional[str] = "standard"


class ComponentThreeBenchmarkRequest(BaseModel):
    scenario: str = "video"
    iterations: int = Field(default=10, ge=1, le=100)


class SecurityActionRequest(BaseModel):
    source: str = "security"
    action: str
    subject: str
    severity: int = 3
    reason: Optional[str] = None


class ComponentFourSegmentationPolicyRequest(BaseModel):
    src_zone: str = "web"
    dst_zone: str = "app"
    ports: List[int] = Field(default_factory=lambda: [443])
    protocol: str = "tcp"
    description: Optional[str] = None


class ComponentFourFlowEvaluationRequest(BaseModel):
    src_ip: str = "10.0.0.1"
    dst_ip: str = "10.0.0.12"
    dst_port: int = Field(default=3306, ge=1, le=65535)
    protocol: str = "tcp"


class ComponentFourIndicatorRequest(BaseModel):
    value: str = "198.51.100.1"
    ioc_type: str = "ip"
    threat_type: str = "Malicious IP"
    severity: str = "high"
    source: str = "manual"


class ComponentFourCtiBlockRequest(BaseModel):
    value: str = "198.51.100.1"
    reason: Optional[str] = None


class ComponentFourAlertRequest(BaseModel):
    src_ip: str = "91.108.4.1"
    signature: str = "SURICATA DDoS source detected"
    severity: int = Field(default=1, ge=1, le=5)
    threat_type: str = "DDoS"


class IntegratedRunRequest(BaseModel):
    scenario: str = Field(default="mixed")
    reset: bool = False
    workload_requests: int = Field(default=24, ge=1, le=250)
    include_security: bool = True
    include_monitoring: bool = True
    include_intent: bool = True


class IntegratedAutomationRequest(BaseModel):
    strategy: str = Field(default='adaptive')
    preferred_scenario: str = Field(default='mixed')
    scenario_sequence: List[str] = Field(default_factory=lambda: ['normal', 'congestion', 'mixed', 'ddos'])
    interval_sec: float = Field(default=15.0, ge=1.0, le=300.0)
    workload_requests: int = Field(default=24, ge=1, le=250)
    include_security: bool = True
    include_monitoring: bool = True
    include_intent: bool = True
    reset_on_start: bool = False
    max_cycles: Optional[int] = Field(default=None, ge=1, le=10000)


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
