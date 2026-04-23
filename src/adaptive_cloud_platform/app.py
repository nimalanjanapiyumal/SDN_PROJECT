from __future__ import annotations

import os
import importlib.util
import shutil
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, start_http_server
from fastapi.responses import FileResponse, Response
from pathlib import Path

from adaptive_cloud_platform.config import get_runtime_config
from adaptive_cloud_platform.models import (
    ComponentOneBackendHealthUpdate,
    ComponentOneBackendMetricUpdate,
    ComponentOnePortStatsUpdate,
    ComponentOneRouteRequest,
    ComponentOneWorkloadSimulationRequest,
    ComponentTwoTelemetryRequest,
    ComponentTwoTrainingRequest,
    ContextUpdate,
    IntentRequest,
    PolicyEnforcementRequest,
    ResourcePlanRequest,
    SecurityActionRequest,
    SessionLoginRequest,
    SessionVerifyRequest,
)
from adaptive_cloud_platform.state import IntegratedState
from adaptive_cloud_platform.adapters.execution_adapter import ExecutionAdapter
from adaptive_cloud_platform.services.orchestrator_service import OrchestratorService
from adaptive_cloud_platform.services.resource_optimizer_service import ResourceOptimizerService
from adaptive_cloud_platform.services.ml_service import MLService
from adaptive_cloud_platform.services.monitoring_ml_service import MonitoringMLService
from adaptive_cloud_platform.services.security_service import SecurityService

runtime = get_runtime_config()
state = IntegratedState()
adapter = ExecutionAdapter()
orchestrator = OrchestratorService(state, adapter)
optimizer = ResourceOptimizerService(runtime.system_config)
ml_service = MLService()
monitoring_ml_service = MonitoringMLService(ml_service)
security_service = SecurityService()

app = FastAPI(title='Adaptive Cloud SDN Integrated API', version='1.0.0')
FRONTEND_DIR = Path(__file__).resolve().parent / 'frontend'
app.mount('/frontend', StaticFiles(directory=FRONTEND_DIR), name='frontend')

METRIC_DECISIONS = Counter('adaptive_decisions_total', 'Total decisions made by the integrated orchestrator')
METRIC_SECURITY = Counter('adaptive_security_actions_total', 'Total security actions received by the orchestrator')
METRIC_COMPONENT1_ROUTES = Counter('adaptive_component1_routes_total', 'Total Component 1 hybrid routing decisions')
METRIC_COMPONENT1_GA = Counter('adaptive_component1_ga_recomputes_total', 'Total Component 1 GA recomputations')
METRIC_COMPONENT2_PREDICTIONS = Counter('adaptive_component2_predictions_total', 'Total Component 2 ML predictions', ['label'])
METRIC_COMPONENT2_POLICY_FEEDBACK = Counter('adaptive_component2_policy_feedback_total', 'Total Component 2 policy feedback events')
METRIC_LAST_SCORE = Gauge('adaptive_last_decision_score', 'Score of last decision')
METRIC_COMPONENT2_CONFIDENCE = Gauge('adaptive_component2_prediction_confidence', 'Latest Component 2 prediction confidence')
METRIC_COMPONENT2_SLA_RISK = Gauge('adaptive_component2_sla_risk_score', 'Latest Component 2 SLA risk score')

# Start a dedicated exporter endpoint for Prometheus scraping
try:
    start_http_server(runtime.prometheus_exporter_port, addr='0.0.0.0')
except OSError:
    pass


@app.get('/', include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / 'index.html')


@app.get('/favicon.ico', include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / 'favicon.svg', media_type='image/svg+xml')


@app.get('/healthz')
def healthz() -> dict:
    return {'status': 'ok', 'ts': time.time()}


@app.get('/metrics')
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post('/api/v1/intents')
def post_intent(payload: IntentRequest) -> dict:
    recorded = orchestrator.record_intent(payload.model_dump())
    allocation = optimizer.apply_intent_feedback(recorded)
    if allocation.get('route_result', {}).get('accepted'):
        METRIC_COMPONENT1_ROUTES.inc()
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'intent': recorded, 'component_1_allocation': allocation, 'decision': decision}


@app.post('/api/v1/context')
def post_context(payload: ContextUpdate) -> dict:
    started_at = time.time()
    data = payload.model_dump(exclude_none=True)
    if not data.get('recommendation'):
        inference = monitoring_ml_service.predict(data)
        data.update(inference)
    else:
        inference = {
            'label': data.get('label') or 'external',
            'recommendation': data.get('recommendation'),
            'confidence': data.get('confidence', 0.0),
            'sla_risk_score': data.get('sla_risk_score', 0.0),
            'source': data.get('source', 'monitoring'),
        }
    METRIC_COMPONENT2_PREDICTIONS.labels(label=str(inference.get('label', 'unknown'))).inc()
    METRIC_COMPONENT2_CONFIDENCE.set(float(inference.get('confidence', 0.0) or 0.0))
    METRIC_COMPONENT2_SLA_RISK.set(float(inference.get('sla_risk_score', 0.0) or 0.0))
    recorded = orchestrator.record_context(data)
    allocation = optimizer.apply_context_feedback(recorded)
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
    if allocation.get('triggered'):
        METRIC_COMPONENT2_POLICY_FEEDBACK.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    mitigation_latency_ms = (time.time() - started_at) * 1000.0 if allocation.get('triggered') or decision else None
    observation = monitoring_ml_service.record_observation(
        recorded,
        inference,
        policy_result={'allocation': allocation, 'decision': decision},
        mitigation_latency_ms=mitigation_latency_ms,
    )
    return {
        'accepted': True,
        'context': recorded,
        'component_2_prediction': inference,
        'component_2_observation': observation,
        'component_1_allocation': allocation,
        'decision': decision,
    }


@app.post('/api/v1/resource-plans')
def post_resource_plan(payload: ResourcePlanRequest) -> dict:
    recorded = orchestrator.record_resource_plan(payload.model_dump())
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'resource_plan': recorded, 'decision': decision}


@app.post('/api/v1/security-actions')
def post_security_action(payload: SecurityActionRequest) -> dict:
    recorded = orchestrator.record_security_action(payload.model_dump())
    METRIC_SECURITY.inc()
    allocation = optimizer.apply_security_feedback(recorded)
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'security_action': recorded, 'component_1_allocation': allocation, 'decision': decision}


@app.get('/api/v1/state')
def get_state() -> dict:
    return state.snapshot()


@app.get('/api/v1/backends')
def get_backends() -> dict:
    return {'backends': optimizer.backend_summary()}


@app.post('/api/v1/resource-plans/recompute')
def recompute_resource_plan() -> dict:
    plan = optimizer.build_plan()
    METRIC_COMPONENT1_GA.inc()
    orchestrator.record_resource_plan(plan)
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'plan': plan, 'decision': decision}


# ------------------------------------------------------------------
# Component 1: Hybrid Load Balancing and Cloud Resource Allocation
# ------------------------------------------------------------------
@app.get('/api/v1/component-1/status')
def component_one_status() -> dict:
    return optimizer.component_status()


@app.get('/api/v1/component-1/platform')
def component_one_platform() -> dict:
    return {
        'integrated_backend_mode': 'fastapi_simulated_flow_manager',
        'execution_adapter_mode': adapter.mode,
        'real_sdn_push_from_integrated_api': False,
        'local_tools': {
            'ryu_manager': shutil.which('ryu-manager'),
            'mininet_mn': shutil.which('mn'),
            'openstack': shutil.which('openstack'),
        },
        'python_modules': {
            'ryu': importlib.util.find_spec('ryu') is not None,
            'mininet': importlib.util.find_spec('mininet') is not None,
            'openstack': importlib.util.find_spec('openstack') is not None,
        },
        'source_integrations': {
            'component_1_ryu_controller': 'sources/SDN_CLOUD_1-master/vm-a1-controller/sdn_hybrid_lb/controller/ryu_app.py',
            'component_1_flow_manager': 'sources/SDN_CLOUD_1-master/vm-a1-controller/sdn_hybrid_lb/controller/flow_manager.py',
            'mininet_topology': 'sources/SDN_CLOUD_1-master/vm-a2-dataplane/mininet/topo_lb.py',
            'openstack_dashboard_support': 'sources/SDN_CLOUD_1-master/dashboard/flask_dashboard/app.py',
        },
        'note': 'Run the source Ryu/Mininet stack on Ubuntu/Linux for real OpenFlow packet-in and OFPFlowMod enforcement.',
    }


# ------------------------------------------------------------------
# Component 2: Monitoring, Visualization, and ML-Based Optimization
# ------------------------------------------------------------------
@app.get('/api/v1/component-2/status')
def component_two_status() -> dict:
    return monitoring_ml_service.status()


@app.get('/api/v1/component-2/platform')
def component_two_platform() -> dict:
    return monitoring_ml_service.platform_status()


@app.post('/api/v1/component-2/telemetry')
def component_two_telemetry(payload: ComponentTwoTelemetryRequest) -> dict:
    return post_context(ContextUpdate(**payload.model_dump(exclude_none=True)))


@app.get('/api/v1/component-2/scenarios/{scenario_name}')
def component_two_scenario(scenario_name: str) -> dict:
    metrics = monitoring_ml_service.scenario_metrics(scenario_name)
    prediction = monitoring_ml_service.predict(metrics)
    return {'scenario': scenario_name, 'metrics': metrics, 'prediction': prediction}


@app.post('/api/v1/component-2/models/train')
def component_two_train_models(payload: ComponentTwoTrainingRequest) -> dict:
    report = monitoring_ml_service.train_models(payload.samples_per_class, payload.seed)
    return {'trained': True, 'report': report, 'models': monitoring_ml_service.model_status()}


@app.post('/api/v1/component-1/route')
def component_one_route(payload: ComponentOneRouteRequest) -> dict:
    result = optimizer.route_request(**payload.model_dump())
    if result.get('accepted'):
        METRIC_COMPONENT1_ROUTES.inc()
    return result


@app.get('/api/v1/component-1/flows')
def component_one_flows() -> dict:
    status = optimizer.component_status()
    return {
        'active_flows': status['active_flows'],
        'flow_rules': status['flow_rules'],
    }


@app.post('/api/v1/component-1/backends/{backend_name}/metrics')
def component_one_backend_metrics(backend_name: str, payload: ComponentOneBackendMetricUpdate) -> dict:
    return optimizer.update_backend_metrics(backend_name, **payload.model_dump())


@app.post('/api/v1/component-1/backends/{backend_name}/health')
def component_one_backend_health(backend_name: str, payload: ComponentOneBackendHealthUpdate) -> dict:
    return optimizer.set_backend_health(backend_name, payload.healthy, payload.reason)


@app.post('/api/v1/component-1/port-stats')
def component_one_port_stats(payload: ComponentOnePortStatsUpdate) -> dict:
    return optimizer.update_port_stats(**payload.model_dump())


@app.post('/api/v1/component-1/workload/simulate')
def component_one_workload_simulation(payload: ComponentOneWorkloadSimulationRequest) -> dict:
    result = optimizer.simulate_workload(**payload.model_dump())
    if result.get('routed'):
        METRIC_COMPONENT1_ROUTES.inc(float(result['routed']))
    if result.get('latest_plan'):
        METRIC_COMPONENT1_GA.inc()
    return result


@app.post('/api/v1/component-1/reset')
def component_one_reset() -> dict:
    return optimizer.reset_runtime()


# ------------------------------------------------------------------
# Compatibility layer for existing team module endpoints
# ------------------------------------------------------------------
@app.post('/api/intent/submit')
def compat_submit_intent(payload: IntentRequest) -> dict:
    return post_intent(payload)


@app.post('/api/context/update')
def compat_update_context(payload: ContextUpdate) -> dict:
    return post_context(payload)


@app.get('/api/network/hosts')
def compat_hosts() -> dict:
    return {'total_hosts': len(state.hosts), 'hosts': state.hosts}


@app.get('/api/metrics/get')
def compat_metrics() -> dict:
    snap = state.snapshot()
    return {
        'metrics': {
            'intents_received': len(snap['intents']),
            'contexts_received': len(snap['contexts']),
            'plans_received': len(snap['resource_plans']),
            'security_received': len(snap['security_actions']),
            'decisions': len(snap['decisions']),
        },
        'context': snap['contexts'][-1] if snap['contexts'] else {},
    }


@app.post('/api/v1/policy/enforce')
def compat_policy_enforce(payload: PolicyEnforcementRequest) -> dict:
    if payload.type in {'block', 'quarantine', 'release', 'allow'}:
        action = security_service.build_action(
            action=payload.type,
            subject=payload.src_ip or payload.dst_ip or 'unknown',
            reason=payload.reason,
            severity=4 if payload.type in {'block', 'quarantine'} else 2,
        )
        return post_security_action(SecurityActionRequest(**action))
    return post_intent(IntentRequest(type=payload.type, src_ip=payload.src_ip, dst_ip=payload.dst_ip, priority=4, metadata={'reason': payload.reason, 'duration': payload.duration}))


@app.post('/sdn/block')
def compat_block(payload: dict) -> dict:
    action = security_service.build_action('block', payload.get('ip', 'unknown'), payload.get('reason', 'compat block'), 5)
    return post_security_action(SecurityActionRequest(**action))


@app.post('/sdn/quarantine')
def compat_quarantine(payload: dict) -> dict:
    action = security_service.build_action('quarantine', payload.get('ip', 'unknown'), payload.get('reason', 'compat quarantine'), 5)
    return post_security_action(SecurityActionRequest(**action))


@app.post('/sdn/release')
def compat_release(payload: dict) -> dict:
    action = security_service.build_action('release', payload.get('ip', 'unknown'), payload.get('reason', 'compat release'), 2)
    return post_security_action(SecurityActionRequest(**action))
