from __future__ import annotations

import os
import importlib.util
import shutil
import time
import subprocess
import urllib.request
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
    ComponentFourAlertRequest,
    ComponentFourCtiBlockRequest,
    ComponentFourFlowEvaluationRequest,
    ComponentFourIndicatorRequest,
    ComponentFourSegmentationPolicyRequest,
    ComponentThreeBenchmarkRequest,
    ComponentThreeContextUpdate,
    ComponentThreeIntentRequest,
    ComponentTwoTelemetryRequest,
    ComponentTwoTrainingRequest,
    ContextUpdate,
    IntegratedRunRequest,
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
from adaptive_cloud_platform.services.intent_controller_service import IntentControllerService
from adaptive_cloud_platform.services.security_service import SecurityService

runtime = get_runtime_config()
state = IntegratedState()
adapter = ExecutionAdapter()
orchestrator = OrchestratorService(state, adapter)
optimizer = ResourceOptimizerService(runtime.system_config)
ml_service = MLService()
monitoring_ml_service = MonitoringMLService(ml_service)
intent_controller_service = IntentControllerService(state)
security_service = SecurityService(state)
integrated_run_history: list[dict] = []

app = FastAPI(title='Adaptive Cloud SDN Integrated API', version='1.0.0')
FRONTEND_DIR = Path(__file__).resolve().parent / 'frontend'
app.mount('/frontend', StaticFiles(directory=FRONTEND_DIR), name='frontend')

METRIC_DECISIONS = Counter('adaptive_decisions_total', 'Total decisions made by the integrated orchestrator')
METRIC_SECURITY = Counter('adaptive_security_actions_total', 'Total security actions received by the orchestrator')
METRIC_COMPONENT1_ROUTES = Counter('adaptive_component1_routes_total', 'Total Component 1 hybrid routing decisions')
METRIC_COMPONENT1_GA = Counter('adaptive_component1_ga_recomputes_total', 'Total Component 1 GA recomputations')
METRIC_COMPONENT2_PREDICTIONS = Counter('adaptive_component2_predictions_total', 'Total Component 2 ML predictions', ['label'])
METRIC_COMPONENT2_POLICY_FEEDBACK = Counter('adaptive_component2_policy_feedback_total', 'Total Component 2 policy feedback events')
METRIC_COMPONENT3_INTENTS = Counter('adaptive_component3_intents_total', 'Total Component 3 translated intents', ['intent_type'])
METRIC_COMPONENT3_RULES = Counter('adaptive_component3_rules_total', 'Total Component 3 generated flow rules', ['intent_type'])
METRIC_COMPONENT3_CONTEXT_UPDATES = Counter('adaptive_component3_context_updates_total', 'Total Component 3 context adaptation updates')
METRIC_COMPONENT4_AUTH_CHECKS = Counter('adaptive_component4_auth_checks_total', 'Total Component 4 continuous authentication checks', ['result'])
METRIC_COMPONENT4_SECURITY_RULES = Counter('adaptive_component4_security_rules_total', 'Total Component 4 security rules generated', ['action'])
METRIC_COMPONENT4_CTI_EVENTS = Counter('adaptive_component4_cti_events_total', 'Total Component 4 CTI events', ['result'])
METRIC_INTEGRATED_RUNS = Counter('adaptive_integrated_runs_total', 'Total autonomous integrated model runs', ['scenario'])
METRIC_LAST_SCORE = Gauge('adaptive_last_decision_score', 'Score of last decision')
METRIC_COMPONENT2_CONFIDENCE = Gauge('adaptive_component2_prediction_confidence', 'Latest Component 2 prediction confidence')
METRIC_COMPONENT2_SLA_RISK = Gauge('adaptive_component2_sla_risk_score', 'Latest Component 2 SLA risk score')
METRIC_COMPONENT3_CONTEXT_SCORE = Gauge('adaptive_component3_context_score', 'Latest Component 3 multi-dimensional context score')
METRIC_COMPONENT3_TRANSLATION_LATENCY = Gauge('adaptive_component3_translation_latency_ms', 'Latest Component 3 intent translation latency')
METRIC_COMPONENT3_ACTIVE_RULES = Gauge('adaptive_component3_active_rules', 'Component 3 active rule count')
METRIC_COMPONENT4_ACTIVE_RULES = Gauge('adaptive_component4_active_rules', 'Component 4 active security rule count')
METRIC_COMPONENT4_RISK_SCORE = Gauge('adaptive_component4_latest_risk_score', 'Latest Component 4 authentication anomaly score')
METRIC_COMPONENT4_MITIGATION_LATENCY = Gauge('adaptive_component4_mitigation_latency_ms', 'Latest Component 4 mitigation latency')
METRIC_INTEGRATED_RUN_LATENCY = Gauge('adaptive_integrated_run_latency_ms', 'Latest integrated model run latency')

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


def _record_decision_metrics(decision: dict | None) -> None:
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))


def _record_component4_metrics(result: dict | None) -> None:
    if not result:
        return
    rule = result.get('rule') or {}
    action = str(result.get('action') or rule.get('action') or 'unknown')
    METRIC_COMPONENT4_SECURITY_RULES.labels(action=action).inc()
    METRIC_COMPONENT4_ACTIVE_RULES.set(float(len(security_service.active_rules())))
    if result.get('latency_ms') is not None:
        METRIC_COMPONENT4_MITIGATION_LATENCY.set(float(result.get('latency_ms') or 0.0))


def _probe_http(url: str, timeout: float = 1.5) -> dict:
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                'url': url,
                'reachable': True,
                'status': int(response.status),
                'latency_ms': round((time.time() - started) * 1000.0, 2),
            }
    except Exception as exc:
        return {
            'url': url,
            'reachable': False,
            'error': str(exc),
            'latency_ms': round((time.time() - started) * 1000.0, 2),
        }


def _tool_status(names: list[str]) -> dict:
    return {name: shutil.which(name) for name in names}


def _module_status(names: list[str]) -> dict:
    return {name: importlib.util.find_spec(name) is not None for name in names}


def _wsl_status() -> dict:
    try:
        result = subprocess.run(['wsl', '-l', '-v'], capture_output=True, text=True, timeout=4)
        return {
            'available': result.returncode == 0,
            'returncode': result.returncode,
            'output': (result.stdout or result.stderr).strip(),
        }
    except Exception as exc:
        return {'available': False, 'error': str(exc)}


def _process_intent_payload(payload: dict) -> dict:
    translation = intent_controller_service.submit_intent(payload)
    translated_intent = translation['intent']
    METRIC_COMPONENT3_INTENTS.labels(intent_type=str(translated_intent.get('type', 'generic'))).inc()
    for rule in translation.get('rules', []):
        METRIC_COMPONENT3_RULES.labels(intent_type=str(rule.get('intent_type', 'generic'))).inc()
    METRIC_COMPONENT3_CONTEXT_SCORE.set(float(translation.get('benchmark', {}).get('context_score', 0.0) or 0.0))
    METRIC_COMPONENT3_TRANSLATION_LATENCY.set(float(translation.get('benchmark', {}).get('translation_latency_ms', 0.0) or 0.0))
    METRIC_COMPONENT3_ACTIVE_RULES.set(float(len(intent_controller_service.active_rules())))

    recorded = orchestrator.record_intent(translated_intent)
    allocation = optimizer.apply_intent_feedback(recorded)
    if (allocation.get('route_result') or {}).get('accepted'):
        METRIC_COMPONENT1_ROUTES.inc()
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    _record_decision_metrics(decision)
    return {
        'accepted': True,
        'intent': recorded,
        'component_3_translation': translation,
        'component_1_allocation': allocation,
        'decision': decision,
    }


def _lightweight_platform_readiness() -> dict:
    root = Path.cwd()
    monitoring_files = [
        root / 'monitoring/prometheus/prometheus.yml',
        root / 'monitoring/grafana/dashboards/overview.json',
        root / 'monitoring/grafana/provisioning/datasources/prometheus.yml',
        root / 'docker-compose.yml',
    ]
    sdn_files = [
        root / 'src/adaptive_cloud_platform/sdn/ryu_integrated_app.py',
        root / 'src/topology/adaptive_cloud_topology.py',
        root / 'docs/RYU_MININET_RUNBOOK.md',
    ]
    monitoring_tools = _tool_status(['docker', 'prometheus', 'grafana-server'])
    sdn_tools = _tool_status(['ryu-manager', 'mn', 'ovs-ofctl', 'suricata'])
    return {
        'monitoring': {
            'files_ready': all(path.exists() for path in monitoring_files),
            'available_tools': [name for name, path in monitoring_tools.items() if path],
            'expected_urls': {
                'api': 'http://127.0.0.1:8080/',
                'metrics': f'http://127.0.0.1:{runtime.prometheus_exporter_port}/metrics',
                'prometheus': 'http://127.0.0.1:9090',
                'grafana': 'http://127.0.0.1:3000',
            },
        },
        'sdn_lab': {
            'files_ready': all(path.exists() for path in sdn_files),
            'available_tools': [name for name, path in sdn_tools.items() if path],
            'required_tools': list(sdn_tools.keys()),
            'real_dataplane_ready': bool(sdn_tools.get('ryu-manager') and sdn_tools.get('mn')),
        },
    }


@app.post('/api/v1/intents')
def post_intent(payload: IntentRequest) -> dict:
    return _process_intent_payload(payload.model_dump(exclude_none=True))


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
    component_3_context = intent_controller_service.update_context(recorded)
    METRIC_COMPONENT3_CONTEXT_UPDATES.inc()
    METRIC_COMPONENT3_CONTEXT_SCORE.set(float(intent_controller_service.context_score()))
    METRIC_COMPONENT3_ACTIVE_RULES.set(float(len(intent_controller_service.active_rules())))
    allocation = optimizer.apply_context_feedback(recorded)
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
    if allocation.get('triggered'):
        METRIC_COMPONENT2_POLICY_FEEDBACK.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    _record_decision_metrics(decision)
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
        'component_3_context': component_3_context,
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
    security_result = security_service.enforce_action(recorded)
    _record_component4_metrics(security_result)
    allocation = optimizer.apply_security_feedback(recorded)
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    if decision:
        METRIC_DECISIONS.inc()
        METRIC_LAST_SCORE.set(float(decision['score']))
    return {
        'accepted': True,
        'security_action': recorded,
        'component_4_enforcement': security_result,
        'component_1_allocation': allocation,
        'decision': decision,
    }


@app.get('/api/v1/state')
def get_state() -> dict:
    return state.snapshot()


@app.get('/api/v1/backends')
def get_backends() -> dict:
    return {'backends': optimizer.backend_summary()}


@app.get('/api/v1/integrated/status')
def integrated_status() -> dict:
    readiness = _lightweight_platform_readiness()
    c1_metrics = optimizer.component_status()['metrics']
    c2_metrics = monitoring_ml_service.status()['metrics']
    c3_metrics = intent_controller_service.status()['metrics']
    c4_metrics = security_service.status()['metrics']
    operator_health = {
        'components_modelled': 4,
        'automatic_pipeline_ready': True,
        'observability_files_ready': readiness['monitoring']['files_ready'],
        'sdn_lab_files_ready': readiness['sdn_lab']['files_ready'],
        'real_sdn_runtime_ready': readiness['sdn_lab']['real_dataplane_ready'],
    }
    return {
        'operator_health': operator_health,
        'readiness': readiness,
        'component_1': c1_metrics,
        'component_2': c2_metrics,
        'component_3': c3_metrics,
        'component_4': c4_metrics,
        'latest_decision': state.decisions[-1] if state.decisions else None,
        'active_policies': state.active_policies,
        'integrated_runs': {
            'count': len(integrated_run_history),
            'latest': integrated_run_history[-1] if integrated_run_history else None,
        },
    }


@app.post('/api/v1/integrated/run')
def integrated_run(payload: IntegratedRunRequest) -> dict:
    started = time.time()
    scenario = payload.scenario.lower()
    if payload.reset:
        optimizer.reset_runtime()
        security_service.reset_runtime()

    scenario_map = {
        'normal': {'c2': 'normal', 'c3': 'video', 'c4': 'insider'},
        'congestion': {'c2': 'congestion', 'c3': 'load', 'c4': 'insider'},
        'ddos': {'c2': 'ddos', 'c3': 'security', 'c4': 'ddos'},
        'port_scan': {'c2': 'port_scan', 'c3': 'security', 'c4': 'port_scan'},
        'security': {'c2': 'ddos', 'c3': 'security', 'c4': 'ddos'},
        'mixed': {'c2': 'congestion', 'c3': 'multi', 'c4': 'ddos'},
    }
    selected = scenario_map.get(scenario, scenario_map['mixed'])
    steps: list[dict] = []

    if payload.include_monitoring:
        metrics = monitoring_ml_service.scenario_metrics(selected['c2'])
        telemetry = component_two_telemetry(ComponentTwoTelemetryRequest(
            **metrics,
            observed_label=selected['c2'] if selected['c2'] in {'normal', 'congestion', 'ddos', 'port_scan'} else None,
            top_talker_src_ip='10.0.0.1',
            top_talker_dst_ip='10.0.0.12',
        ))
        steps.append({
            'component': 2,
            'action': 'telemetry_prediction',
            'label': telemetry.get('component_2_prediction', {}).get('label'),
            'recommendation': telemetry.get('component_2_prediction', {}).get('recommendation'),
            'allocation_triggered': telemetry.get('component_1_allocation', {}).get('triggered'),
        })

    if payload.include_intent:
        intent_scenario = intent_controller_service.scenario(selected['c3'])
        intent_result = component_three_intent(ComponentThreeIntentRequest(**intent_scenario['intent_payload']))
        context_result = component_three_context(ComponentThreeContextUpdate(**intent_scenario['context_payload']))
        steps.append({
            'component': 3,
            'action': 'intent_and_context',
            'intent_type': intent_result.get('component_3_translation', {}).get('classification', {}).get('type'),
            'rules': len(intent_result.get('component_3_translation', {}).get('rules', [])),
            'adapted_rules': context_result.get('component_3_context', {}).get('adapted_rules', 0),
        })

    workload = component_one_workload_simulation(ComponentOneWorkloadSimulationRequest(
        requests=payload.workload_requests,
        clients=['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.7'],
        start_port=47000,
        vip_port=8000,
        request_size_kb=128.0,
        recompute_after=True,
        inject_fault_backend=None,
    ))
    steps.append({
        'component': 1,
        'action': 'automatic_workload',
        'routed': workload.get('routed'),
        'failures': workload.get('failures'),
        'distribution': workload.get('distribution'),
    })

    if payload.include_security:
        security_scenario = security_service.scenario(selected['c4'])
        security_steps: dict[str, object] = {'component': 4, 'action': 'security_enforcement'}
        if security_scenario.get('flow'):
            flow = security_scenario['flow']
            flow_result = component_four_evaluate_flow(ComponentFourFlowEvaluationRequest(**flow))
            security_steps['flow_allowed'] = flow_result.get('allowed')
            security_steps['flow_reason'] = flow_result.get('reason')
        if security_scenario.get('alert'):
            alert_result = component_four_cti_alert(ComponentFourAlertRequest(**security_scenario['alert']))
            security_steps['alert_blocked'] = alert_result.get('should_block')
        if security_scenario.get('indicator'):
            indicator = security_scenario['indicator']
            add_result = component_four_add_indicator(ComponentFourIndicatorRequest(**indicator))
            block_result = component_four_block_indicator(ComponentFourCtiBlockRequest(value=indicator['value'], reason='integrated scenario'))
            security_steps['indicator_added'] = add_result.get('added')
            security_steps['indicator_blocked'] = block_result.get('blocked')
        steps.append(security_steps)

    latency_ms = (time.time() - started) * 1000.0
    METRIC_INTEGRATED_RUNS.labels(scenario=scenario).inc()
    METRIC_INTEGRATED_RUN_LATENCY.set(latency_ms)
    run_record = {
        'scenario': scenario,
        'latency_ms': round(latency_ms, 2),
        'steps': steps,
        'ts': time.time(),
    }
    integrated_run_history.append(run_record)
    return {
        'ran': True,
        'scenario': scenario,
        'latency_ms': round(latency_ms, 2),
        'steps': steps,
        'summary': integrated_status(),
    }


@app.get('/api/v1/platform/validate')
def platform_validate() -> dict:
    root = Path.cwd()
    monitoring_files = {
        'prometheus_config': str(root / 'monitoring/prometheus/prometheus.yml'),
        'grafana_dashboard': str(root / 'monitoring/grafana/dashboards/overview.json'),
        'grafana_datasource': str(root / 'monitoring/grafana/provisioning/datasources/prometheus.yml'),
        'grafana_dashboard_provider': str(root / 'monitoring/grafana/provisioning/dashboards/dashboards.yml'),
    }
    sdn_files = {
        'integrated_ryu_app': str(root / 'src/adaptive_cloud_platform/sdn/ryu_integrated_app.py'),
        'mininet_topology': str(root / 'src/topology/cloud_three_tier_topology.py'),
        'traffic_topology': str(root / 'src/topology/adaptive_cloud_topology.py'),
        'runbook': str(root / 'docs/RYU_MININET_RUNBOOK.md'),
    }
    return {
        'observability': {
            'tools': _tool_status(['docker', 'prometheus', 'grafana-server']),
            'files': {key: {'path': value, 'exists': Path(value).exists()} for key, value in monitoring_files.items()},
            'probes': {
                'api_metrics': _probe_http('http://127.0.0.1:9108/metrics'),
                'prometheus': _probe_http('http://127.0.0.1:9090/-/ready'),
                'grafana': _probe_http('http://127.0.0.1:3000/api/health'),
            },
        },
        'sdn_lab': {
            'tools': _tool_status(['ryu-manager', 'mn', 'ovs-ofctl', 'ovs-vsctl', 'iperf3', 'suricata']),
            'python_modules': _module_status(['ryu', 'mininet', 'networkx']),
            'files': {key: {'path': value, 'exists': Path(value).exists()} for key, value in sdn_files.items()},
            'wsl': _wsl_status(),
            'mode': 'ready_for_linux_sdn_lab' if shutil.which('ryu-manager') and shutil.which('mn') else 'record_only_on_current_host',
        },
    }


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


# ------------------------------------------------------------------
# Component 3: Context-Aware Intent-Based Flow Programming
# ------------------------------------------------------------------
@app.get('/api/v1/component-3/status')
def component_three_status() -> dict:
    status = intent_controller_service.status()
    METRIC_COMPONENT3_CONTEXT_SCORE.set(float(status['metrics']['context_score']))
    METRIC_COMPONENT3_ACTIVE_RULES.set(float(status['metrics']['active_rules']))
    return status


@app.get('/api/v1/component-3/platform')
def component_three_platform() -> dict:
    return intent_controller_service.platform_status()


@app.get('/api/v1/component-3/hosts')
def component_three_hosts() -> dict:
    return intent_controller_service.hosts()


@app.post('/api/v1/component-3/intents')
def component_three_intent(payload: ComponentThreeIntentRequest) -> dict:
    return _process_intent_payload(payload.model_dump(exclude_none=True))


@app.post('/api/v1/component-3/context')
def component_three_context(payload: ComponentThreeContextUpdate) -> dict:
    data = payload.model_dump(exclude_none=True)
    recorded = orchestrator.record_context(data)
    component_3_context = intent_controller_service.update_context(recorded)
    METRIC_COMPONENT3_CONTEXT_UPDATES.inc()
    METRIC_COMPONENT3_CONTEXT_SCORE.set(float(intent_controller_service.context_score()))
    METRIC_COMPONENT3_ACTIVE_RULES.set(float(len(intent_controller_service.active_rules())))
    allocation = optimizer.apply_context_feedback(recorded)
    if allocation.get('plan'):
        METRIC_COMPONENT1_GA.inc()
        orchestrator.record_resource_plan(allocation['plan'])
    decision = orchestrator.decide()
    _record_decision_metrics(decision)
    return {
        'accepted': True,
        'context': recorded,
        'component_3_context': component_3_context,
        'component_1_allocation': allocation,
        'decision': decision,
    }


@app.get('/api/v1/component-3/rules')
def component_three_rules() -> dict:
    return intent_controller_service.rules_status()


@app.get('/api/v1/component-3/scenarios/{scenario_name}')
def component_three_scenario(scenario_name: str) -> dict:
    return intent_controller_service.scenario(scenario_name)


@app.post('/api/v1/component-3/benchmark')
def component_three_benchmark(payload: ComponentThreeBenchmarkRequest) -> dict:
    result = intent_controller_service.benchmark(payload.scenario, payload.iterations)
    METRIC_COMPONENT3_CONTEXT_SCORE.set(float(intent_controller_service.context_score()))
    METRIC_COMPONENT3_ACTIVE_RULES.set(float(len(intent_controller_service.active_rules())))
    return result


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
# Component 4: Adaptive Security Enforcement
# ------------------------------------------------------------------
@app.get('/api/v1/component-4/status')
def component_four_status() -> dict:
    status = security_service.status()
    METRIC_COMPONENT4_ACTIVE_RULES.set(float(status['metrics']['active_security_rules']))
    return status


@app.get('/api/v1/component-4/platform')
def component_four_platform() -> dict:
    return security_service.platform_status()


@app.post('/api/v1/component-4/auth/login')
def component_four_auth_login(payload: SessionLoginRequest) -> dict:
    return security_service.create_session(payload.user_id, payload.ip, payload.password)


@app.post('/api/v1/component-4/auth/verify')
def component_four_auth_verify(payload: SessionVerifyRequest) -> dict:
    result = security_service.verify_session(payload.token, payload.ip, payload.bytes_sent)
    METRIC_COMPONENT4_AUTH_CHECKS.labels(result='allowed' if result.get('allowed') else 'denied').inc()
    session = result.get('session') or {}
    METRIC_COMPONENT4_RISK_SCORE.set(float(session.get('anomaly_score', 0.0) or 0.0))
    action = result.get('security_action')
    enforcement = None
    if action and action.get('action') in {'block', 'quarantine', 'release', 'allow'}:
        enforcement = post_security_action(SecurityActionRequest(**action))
    result['component_4_enforcement'] = enforcement
    return result


@app.get('/api/v1/component-4/auth/sessions')
def component_four_auth_sessions() -> dict:
    return {'sessions': security_service.status()['sessions']}


@app.get('/api/v1/component-4/segmentation/policies')
def component_four_segmentation_policies() -> dict:
    return {'policies': security_service.status()['policies']}


@app.post('/api/v1/component-4/segmentation/policies')
def component_four_add_segmentation_policy(payload: ComponentFourSegmentationPolicyRequest) -> dict:
    return security_service.add_segmentation_policy(
        payload.src_zone,
        payload.dst_zone,
        payload.ports,
        payload.protocol,
        payload.description or '',
    )


@app.post('/api/v1/component-4/segmentation/enforce')
def component_four_enforce_segmentation() -> dict:
    result = security_service.enforce_segmentation_policies()
    for rule in result.get('rules', []):
        METRIC_COMPONENT4_SECURITY_RULES.labels(action=str(rule.get('action', 'segment'))).inc()
    METRIC_COMPONENT4_ACTIVE_RULES.set(float(len(security_service.active_rules())))
    return result


@app.post('/api/v1/component-4/segmentation/evaluate')
def component_four_evaluate_flow(payload: ComponentFourFlowEvaluationRequest) -> dict:
    result = security_service.evaluate_flow(payload.src_ip, payload.dst_ip, payload.dst_port, payload.protocol)
    enforcement = None
    if result.get('security_action'):
        enforcement = post_security_action(SecurityActionRequest(**result['security_action']))
    result['component_4_enforcement'] = enforcement
    return result


@app.get('/api/v1/component-4/cti/indicators')
def component_four_cti_indicators() -> dict:
    return {'indicators': security_service.status()['indicators']}


@app.post('/api/v1/component-4/cti/indicators')
def component_four_add_indicator(payload: ComponentFourIndicatorRequest) -> dict:
    result = security_service.add_indicator(
        payload.value,
        payload.ioc_type,
        payload.threat_type,
        payload.severity,
        payload.source,
    )
    METRIC_COMPONENT4_CTI_EVENTS.labels(result='indicator_added').inc()
    return result


@app.post('/api/v1/component-4/cti/fetch')
def component_four_fetch_cti() -> dict:
    result = security_service.fetch_cti_feed()
    METRIC_COMPONENT4_CTI_EVENTS.labels(result='feed_fetch').inc()
    return result


@app.post('/api/v1/component-4/cti/block')
def component_four_block_indicator(payload: ComponentFourCtiBlockRequest) -> dict:
    result = security_service.block_indicator(payload.value, payload.reason or '')
    enforcement = post_security_action(SecurityActionRequest(**result['security_action']))
    result['component_4_enforcement'] = enforcement
    METRIC_COMPONENT4_CTI_EVENTS.labels(result='blocked').inc()
    return result


@app.post('/api/v1/component-4/cti/alert')
def component_four_cti_alert(payload: ComponentFourAlertRequest) -> dict:
    result = security_service.handle_alert(payload.model_dump())
    enforcement = None
    if result.get('security_action'):
        enforcement = post_security_action(SecurityActionRequest(**result['security_action']))
        METRIC_COMPONENT4_CTI_EVENTS.labels(result='alert_blocked').inc()
    else:
        METRIC_COMPONENT4_CTI_EVENTS.labels(result='alert_observed').inc()
    result['component_4_enforcement'] = enforcement
    return result


@app.get('/api/v1/component-4/rules')
def component_four_rules() -> dict:
    return security_service.rules_status()


@app.get('/api/v1/component-4/scenarios/{scenario_name}')
def component_four_scenario(scenario_name: str) -> dict:
    return security_service.scenario(scenario_name)


@app.post('/api/v1/component-4/reset')
def component_four_reset() -> dict:
    return security_service.reset_runtime()


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
    return intent_controller_service.hosts()


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
            'component_3_rules': len(intent_controller_service.rules),
            'component_3_context_updates': len(intent_controller_service.context_updates),
        },
        'context': snap['contexts'][-1] if snap['contexts'] else {},
        'component_3': intent_controller_service.status()['metrics'],
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


@app.get('/sdn/stats')
def compat_sdn_stats() -> dict:
    return security_service.status()['metrics']


@app.get('/sdn/zones')
def compat_sdn_zones() -> dict:
    return {'policies': security_service.status()['policies']}


@app.post('/auth/login')
def compat_auth_login(payload: SessionLoginRequest) -> dict:
    return component_four_auth_login(payload)


@app.post('/auth/verify')
def compat_auth_verify(payload: SessionVerifyRequest) -> dict:
    return component_four_auth_verify(payload)


@app.get('/auth/sessions')
def compat_auth_sessions() -> dict:
    return component_four_auth_sessions()


@app.post('/seg/enforce')
def compat_seg_enforce() -> dict:
    return component_four_enforce_segmentation()


@app.get('/seg/policies')
def compat_seg_policies() -> dict:
    return component_four_segmentation_policies()


@app.post('/seg/add_policy')
def compat_seg_add_policy(payload: ComponentFourSegmentationPolicyRequest) -> dict:
    return component_four_add_segmentation_policy(payload)


@app.post('/seg/quarantine')
def compat_seg_quarantine(payload: dict) -> dict:
    action = security_service.build_action('quarantine', payload.get('ip', 'unknown'), payload.get('reason', 'segmentation quarantine'), 4)
    return post_security_action(SecurityActionRequest(**action))


@app.get('/seg/flows')
def compat_seg_flows() -> dict:
    return component_four_rules()


@app.get('/cti/stats')
def compat_cti_stats() -> dict:
    status = security_service.status()
    return {
        'total_iocs': status['metrics']['total_iocs'],
        'blocked_ips': status['metrics']['blocked_iocs'],
        'avg_latency_ms': status['metrics']['avg_mitigation_latency_ms'] or 0,
        'indicators': status['indicators'],
    }


@app.post('/cti/fetch')
def compat_cti_fetch() -> dict:
    return component_four_fetch_cti()


@app.post('/cti/block')
def compat_cti_block(payload: dict) -> dict:
    value = payload.get('value') or payload.get('ip') or 'unknown'
    return component_four_block_indicator(ComponentFourCtiBlockRequest(value=value, reason=payload.get('reason')))
