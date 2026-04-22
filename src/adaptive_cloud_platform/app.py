from __future__ import annotations

import os
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, start_http_server
from fastapi.responses import FileResponse, Response
from pathlib import Path

from adaptive_cloud_platform.config import get_runtime_config
from adaptive_cloud_platform.models import (
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
from adaptive_cloud_platform.services.security_service import SecurityService

runtime = get_runtime_config()
state = IntegratedState()
adapter = ExecutionAdapter()
orchestrator = OrchestratorService(state, adapter)
optimizer = ResourceOptimizerService(runtime.system_config)
ml_service = MLService()
security_service = SecurityService()

app = FastAPI(title='Adaptive Cloud SDN Integrated API', version='1.0.0')
FRONTEND_DIR = Path(__file__).resolve().parent / 'frontend'
app.mount('/frontend', StaticFiles(directory=FRONTEND_DIR), name='frontend')

METRIC_DECISIONS = Counter('adaptive_decisions_total', 'Total decisions made by the integrated orchestrator')
METRIC_SECURITY = Counter('adaptive_security_actions_total', 'Total security actions received by the orchestrator')
METRIC_LAST_SCORE = Gauge('adaptive_last_decision_score', 'Score of last decision')

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
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'intent': recorded, 'decision': decision}


@app.post('/api/v1/context')
def post_context(payload: ContextUpdate) -> dict:
    data = payload.model_dump(exclude_none=True)
    if not data.get('recommendation'):
        inference = ml_service.infer(data)
        data.update(inference)
    recorded = orchestrator.record_context(data)
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'context': recorded, 'decision': decision}


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
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'accepted': True, 'security_action': recorded, 'decision': decision}


@app.get('/api/v1/state')
def get_state() -> dict:
    return state.snapshot()


@app.get('/api/v1/backends')
def get_backends() -> dict:
    return {'backends': optimizer.backend_summary()}


@app.post('/api/v1/resource-plans/recompute')
def recompute_resource_plan() -> dict:
    plan = optimizer.build_plan()
    orchestrator.record_resource_plan(plan)
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {'plan': plan, 'decision': decision}


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
