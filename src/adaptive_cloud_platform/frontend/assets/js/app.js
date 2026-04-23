import { componentConfigs } from "../../components/index.js";

const state = {
  selectedComponentId: componentConfigs[0].id,
  snapshot: null,
  componentOne: null,
  componentTwo: null,
  componentThree: null,
  componentFour: null,
  integrated: null,
  latestIntegratedRun: null,
  platformValidation: null,
  integratedRunCount: 0,
  health: null,
  autoRefresh: true,
  timer: null
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  renderComponentNav();
  renderApiMatrix();
  refreshAll();
  state.timer = window.setInterval(() => {
    if (state.autoRefresh) {
      refreshAll({ quiet: true });
    }
  }, 5000);
});

function cacheElements() {
  [
    "apiBase",
    "apiStatus",
    "refreshBtn",
    "autoRefresh",
    "integratedScenario",
    "runIntegratedBtn",
    "validatePlatformBtn",
    "combinedHealth",
    "combinedRuns",
    "combinedLatency",
    "monitoringReady",
    "sdnReady",
    "integratedRunJson",
    "recomputeBtn",
    "routeRequestBtn",
    "componentNav",
    "componentPanel",
    "rrDecisionCount",
    "gaRunCount",
    "activeFlowCount",
    "slaCompliance",
    "slaTarget",
    "healthyBackendCount",
    "latestDecisionTitle",
    "latestBackend",
    "latestAlgorithm",
    "latestLatency",
    "latestDecisionJson",
    "backendList",
    "flowRuleList",
    "eventTimeline",
    "apiMatrix",
    "toast",
    "requestForm",
    "metricForm",
    "simulationForm",
    "metricBackend",
    "simulationFaultBackend",
    "resetComponentBtn"
    ,
    "c2TelemetryCount",
    "c2PredictionCount",
    "c2LatestLabel",
    "c2LatestConfidence",
    "c2RiskScore",
    "c2MitigationLatency",
    "componentTwoTelemetryForm",
    "componentTwoPredictionJson",
    "trainComponentTwoBtn",
    "componentTwoPlatformBtn",
    "c3IntentCount",
    "c3RuleCount",
    "c3AvgLatency",
    "c3ContextScore",
    "componentThreeIntentForm",
    "componentThreeContextForm",
    "componentThreeOutputJson",
    "componentThreePlatformBtn",
    "componentThreeHostsBtn",
    "c4SessionCount",
    "c4SessionRisk",
    "c4QuarantineCount",
    "c4BlockedIocCount",
    "c4RuleCount",
    "c4MitigationLatency",
    "componentFourAuthForm",
    "componentFourSecurityForm",
    "componentFourLoginBtn",
    "componentFourEnforceSegBtn",
    "componentFourFetchCtiBtn",
    "componentFourBlockIocBtn",
    "componentFourPlatformBtn",
    "componentFourRulesBtn",
    "componentFourOutputJson"
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
  els.apiBase.textContent = window.location.origin;
}

function bindEvents() {
  els.refreshBtn.addEventListener("click", () => refreshAll());
  els.runIntegratedBtn.addEventListener("click", runIntegratedModel);
  els.validatePlatformBtn.addEventListener("click", validatePlatformStack);
  els.autoRefresh.addEventListener("change", (event) => {
    state.autoRefresh = event.target.checked;
  });
  els.recomputeBtn.addEventListener("click", recomputePlan);
  els.routeRequestBtn.addEventListener("click", () => routeRequest());
  els.resetComponentBtn.addEventListener("click", resetComponentOne);

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => activateTab(tab.dataset.tab));
  });
  document.querySelectorAll("[data-metric-scenario]").forEach((button) => {
    button.addEventListener("click", () => fillMetricScenario(button.dataset.metricScenario));
  });

  els.requestForm.addEventListener("submit", (event) => {
    event.preventDefault();
    routeRequest();
  });
  els.metricForm.addEventListener("submit", submitMetrics);
  els.simulationForm.addEventListener("submit", runSimulation);
  els.componentTwoTelemetryForm.addEventListener("submit", submitComponentTwoTelemetry);
  els.trainComponentTwoBtn.addEventListener("click", trainComponentTwoModels);
  els.componentTwoPlatformBtn.addEventListener("click", showComponentTwoPlatform);
  els.componentThreeIntentForm.addEventListener("submit", submitComponentThreeIntent);
  els.componentThreeContextForm.addEventListener("submit", submitComponentThreeContext);
  els.componentThreePlatformBtn.addEventListener("click", showComponentThreePlatform);
  els.componentThreeHostsBtn.addEventListener("click", showComponentThreeHosts);
  els.componentFourLoginBtn.addEventListener("click", loginComponentFourSession);
  els.componentFourAuthForm.addEventListener("submit", verifyComponentFourSession);
  els.componentFourSecurityForm.addEventListener("submit", evaluateComponentFourSecurity);
  els.componentFourEnforceSegBtn.addEventListener("click", enforceComponentFourSegmentation);
  els.componentFourFetchCtiBtn.addEventListener("click", fetchComponentFourCti);
  els.componentFourBlockIocBtn.addEventListener("click", blockComponentFourIoc);
  els.componentFourPlatformBtn.addEventListener("click", showComponentFourPlatform);
  els.componentFourRulesBtn.addEventListener("click", showComponentFourRules);
  document.querySelectorAll("[data-c2-scenario]").forEach((button) => {
    button.addEventListener("click", () => fillComponentTwoScenario(button.dataset.c2Scenario));
  });
  document.querySelectorAll("[data-c3-scenario]").forEach((button) => {
    button.addEventListener("click", () => fillComponentThreeScenario(button.dataset.c3Scenario));
  });
  document.querySelectorAll("[data-c4-scenario]").forEach((button) => {
    button.addEventListener("click", () => fillComponentFourScenario(button.dataset.c4Scenario));
  });
}

async function refreshAll(options = {}) {
  setApiStatus("loading", "Refreshing");
  try {
    const [health, snapshot, componentOne, componentTwo, componentThree, componentFour, integrated] = await Promise.all([
      apiRequest("/healthz"),
      apiRequest("/api/v1/state"),
      apiRequest("/api/v1/component-1/status"),
      apiRequest("/api/v1/component-2/status"),
      apiRequest("/api/v1/component-3/status"),
      apiRequest("/api/v1/component-4/status"),
      apiRequest("/api/v1/integrated/status")
    ]);
    state.health = health;
    state.snapshot = snapshot;
    state.componentOne = componentOne;
    state.componentTwo = componentTwo;
    state.componentThree = componentThree;
    state.componentFour = componentFour;
    state.integrated = integrated;
    renderState();
    setApiStatus("online", "Online");
    if (!options.quiet) {
      showToast("Runtime state refreshed");
    }
  } catch (error) {
    setApiStatus("offline", "Offline");
    showToast(error.message || "API request failed", true);
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body.slice(0, 140)}`);
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function renderState() {
  const c1 = state.componentOne || {};
  const metrics = c1.metrics || {};
  const sla = c1.sla || {};

  els.rrDecisionCount.textContent = metrics.rr_decisions || 0;
  els.gaRunCount.textContent = metrics.ga_runs || 0;
  els.activeFlowCount.textContent = c1.active_flows || 0;
  els.slaCompliance.textContent = `${Number(sla.compliance_percent ?? 100).toFixed(1)}%`;
  els.slaTarget.textContent = `target ${Number(sla.target_latency_ms ?? 200).toFixed(0)} ms`;
  els.healthyBackendCount.textContent = `${metrics.healthy_backends || 0}/${metrics.total_backends || 0}`;

  renderLatestAction();
  renderBackendSelectors();
  renderBackends();
  renderFlowRules();
  renderTimeline();
  renderComponentTwo();
  renderComponentThree();
  renderComponentFour();
  renderIntegratedStatus();
  renderComponentPanel();
  renderComponentNav();
  renderWorkspaceVisibility();
}

function renderLatestAction() {
  const c1 = state.componentOne || {};
  const events = c1.events || [];
  const latestEvent = events[events.length - 1];
  const flow = latestEvent?.payload?.id ? latestEvent.payload : lastItem(c1.flow_rules || []);

  if (flow) {
    els.latestDecisionTitle.textContent = prettify(latestEvent?.type || "flow installed");
    els.latestBackend.textContent = flow.backend_name || latestEvent?.backend || "none";
    els.latestAlgorithm.textContent = flow.algorithm || c1.controller?.rr_mode || "smooth_weighted";
    els.latestLatency.textContent = `${Number(flow.estimated_latency_ms || 0).toFixed(1)} ms`;
    els.latestDecisionJson.textContent = JSON.stringify(flow, null, 2);
    return;
  }

  if (latestEvent) {
    els.latestDecisionTitle.textContent = prettify(latestEvent.type);
    els.latestBackend.textContent = latestEvent.backend || "system";
    els.latestAlgorithm.textContent = c1.controller?.rr_mode || "smooth_weighted";
    els.latestLatency.textContent = "0 ms";
    els.latestDecisionJson.textContent = JSON.stringify(latestEvent.payload || {}, null, 2);
    return;
  }

  els.latestDecisionTitle.textContent = "Standby";
  els.latestBackend.textContent = "none";
  els.latestAlgorithm.textContent = c1.controller?.rr_mode || "smooth_weighted";
  els.latestLatency.textContent = "0 ms";
  els.latestDecisionJson.textContent = "{}";
}

function renderComponentNav() {
  const counts = getComponentCounts();
  els.componentNav.innerHTML = componentConfigs.map((component) => {
    const active = component.id === state.selectedComponentId ? "active" : "";
    return `
      <button class="component-nav-item ${active}" type="button" data-component="${component.id}">
        <span>${component.number}</span>
        <strong>${escapeHtml(component.shortTitle)}</strong>
        <em>${counts[component.id] || 0}</em>
      </button>
    `;
  }).join("");

  els.componentNav.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedComponentId = button.dataset.component;
      renderComponentNav();
      renderComponentPanel();
      renderWorkspaceVisibility();
    });
  });
}

function renderWorkspaceVisibility() {
  document.querySelectorAll("[data-workspace]").forEach((section) => {
    section.classList.toggle("workspace-hidden", section.dataset.workspace !== state.selectedComponentId);
  });
}

function renderIntegratedStatus() {
  const integrated = state.integrated || {};
  const health = integrated.operator_health || {};
  const readiness = integrated.readiness || {};
  const runs = integrated.integrated_runs || {};
  const monitoringReady = readiness.monitoring?.files_ready;
  const sdnFilesReady = readiness.sdn_lab?.files_ready;
  const realSdnReady = readiness.sdn_lab?.real_dataplane_ready;
  const latest = state.latestIntegratedRun;

  els.combinedHealth.textContent = health.automatic_pipeline_ready ? "Ready" : "Check";
  state.integratedRunCount = Math.max(state.integratedRunCount || 0, Number(runs.count || 0));
  els.combinedRuns.textContent = state.integratedRunCount || 0;
  els.combinedLatency.textContent = latest?.latency_ms ? `${Number(latest.latency_ms).toFixed(1)} ms latest` : "latency pending";
  els.monitoringReady.textContent = monitoringReady ? "Ready" : "Check";
  els.sdnReady.textContent = realSdnReady ? "Live" : (sdnFilesReady ? "Prepared" : "Check");
  if (!latest && !state.platformValidation) {
    els.integratedRunJson.textContent = JSON.stringify({
      automatic_pipeline: health.automatic_pipeline_ready || false,
      observability_files_ready: monitoringReady || false,
      sdn_lab_files_ready: sdnFilesReady || false,
      real_sdn_runtime_ready: realSdnReady || false
    }, null, 2);
  }
}

function renderComponentPanel() {
  const component = getSelectedComponent();
  const c1 = state.componentOne || {};
  const latestByComponent = {
    "component-1": lastItem(c1.events || []),
    "component-2": lastItem((state.snapshot || {}).contexts || []),
    "component-3": state.componentThree?.latest_intent || lastItem((state.snapshot || {}).intents || []),
    "component-4": state.componentFour?.recent_enforcement_events?.slice(-1)[0] || lastItem((state.snapshot || {}).security_actions || [])
  };
  const latest = latestByComponent[component.id] || {};

  els.componentPanel.innerHTML = `
    <div class="component-hero ${component.accent}">
      <span>${component.number}</span>
      <div>
        <p class="eyebrow">${escapeHtml(component.owner)}</p>
        <h2>${escapeHtml(component.title)}</h2>
        <p>${escapeHtml(component.subtitle)}</p>
      </div>
    </div>
    <div class="feature-strip">
      ${(component.capabilities || []).map((item) => `<article><strong>${escapeHtml(item)}</strong></article>`).join("")}
    </div>
    <div class="component-columns">
      <div>
        <h3>Signals</h3>
        <div class="chips">
          ${(component.signals || []).map((item) => `<code>${escapeHtml(item)}</code>`).join("")}
        </div>
      </div>
      <div>
        <h3>Runtime Payload</h3>
        <pre>${escapeHtml(JSON.stringify(latest, null, 2))}</pre>
      </div>
    </div>
  `;
}

function renderBackendSelectors() {
  const backends = getBackends();
  const currentMetric = els.metricBackend.value;
  const currentFault = els.simulationFaultBackend.value;
  const backendOptions = backends.map((backend) => `<option value="${escapeHtml(backend.name)}">${escapeHtml(backend.name)} (${escapeHtml(backend.ip)})</option>`).join("");
  els.metricBackend.innerHTML = backendOptions;
  els.simulationFaultBackend.innerHTML = `<option value="">None</option>${backendOptions}`;
  if (currentMetric && backends.some((backend) => backend.name === currentMetric)) {
    els.metricBackend.value = currentMetric;
  }
  if (currentFault && backends.some((backend) => backend.name === currentFault)) {
    els.simulationFaultBackend.value = currentFault;
  }
}

function renderBackends() {
  const backends = getBackends();
  if (!backends.length) {
    els.backendList.innerHTML = `<p class="empty">No backend data yet.</p>`;
    return;
  }
  const maxWeight = Math.max(...backends.map((backend) => Number(backend.weight || 0)), 1);
  els.backendList.innerHTML = backends.map((backend) => {
    const weight = Number(backend.weight || 0);
    const width = Math.max(5, Math.round((weight / maxWeight) * 100));
    const metrics = backend.metrics || {};
    const capacity = backend.capacity || {};
    const healthClass = backend.healthy ? "healthy" : "offline";
    return `
      <article class="backend-row ${healthClass}">
        <div class="backend-main">
          <div>
            <strong>${escapeHtml(backend.name)}</strong>
            <span>${escapeHtml(backend.ip)} | dpid ${backend.dpid} port ${backend.port}</span>
          </div>
          <span class="health-pill ${healthClass}">${backend.healthy ? "healthy" : "offline"}</span>
        </div>
        <div class="weight-bar" aria-label="Weight ${weight.toFixed(2)}">
          <span style="width: ${width}%"></span>
        </div>
        <div class="backend-metrics">
          ${metricBadge("CPU", percent(metrics.cpu_util))}
          ${metricBadge("MEM", percent(metrics.mem_util))}
          ${metricBadge("BW", percent(metrics.bw_util))}
          ${metricBadge("LAT", `${Number(metrics.latency_ms || 0).toFixed(0)} ms`)}
          ${metricBadge("CONN", `${metrics.active_connections || 0}/${capacity.max_connections || 100}`)}
        </div>
        <div class="backend-actions">
          <button class="mini-button" type="button" data-health="${escapeHtml(backend.name)}" data-healthy="true">Enable</button>
          <button class="mini-button danger" type="button" data-health="${escapeHtml(backend.name)}" data-healthy="false">Fault</button>
        </div>
      </article>
    `;
  }).join("");

  els.backendList.querySelectorAll("[data-health]").forEach((button) => {
    button.addEventListener("click", () => setBackendHealth(button.dataset.health, button.dataset.healthy === "true"));
  });
}

function renderFlowRules() {
  const flows = (state.componentOne?.flow_rules || []).slice().reverse().slice(0, 10);
  if (!flows.length) {
    els.flowRuleList.innerHTML = `<p class="empty">No flow rules installed yet.</p>`;
    return;
  }
  els.flowRuleList.innerHTML = flows.map((flow) => `
    <article class="flow-rule">
      <div>
        <strong>${escapeHtml(flow.id)}</strong>
        <span>${escapeHtml(flow.client_ip)}:${flow.client_port} -> ${escapeHtml(flow.backend_ip)}:${flow.vip_port}</span>
      </div>
      <div class="flow-rule-meta">
        <span>${escapeHtml(flow.backend_name)}</span>
        <span>prio ${flow.priority}</span>
        <span>${Number(flow.estimated_latency_ms || 0).toFixed(1)} ms</span>
      </div>
    </article>
  `).join("");
}

function renderTimeline() {
  const events = (state.componentOne?.events || []).slice().reverse().slice(0, 12);
  if (!events.length) {
    els.eventTimeline.innerHTML = `<p class="empty">No events yet.</p>`;
    return;
  }

  els.eventTimeline.innerHTML = events.map((event) => `
    <article class="timeline-item">
      <span class="timeline-kind">${escapeHtml(shortKind(event.type))}</span>
      <strong>${escapeHtml(prettify(event.type || "event"))}</strong>
      <time>${formatTime(event.ts)}</time>
    </article>
  `).join("");
}

function renderApiMatrix() {
  const component = componentConfigs[0];
  const coverage = [
    ["RR real-time decision", "POST /api/v1/component-1/route"],
    ["GA long-term optimization", "POST /api/v1/resource-plans/recompute"],
    ["Backend metric ingestion", "POST /api/v1/component-1/backends/{name}/metrics"],
    ["Fault tolerance", "POST /api/v1/component-1/backends/{name}/health"],
    ["Flow rule manager", "GET /api/v1/component-1/flows"],
    ["Performance simulation", "POST /api/v1/component-1/workload/simulate"]
  ];
  els.apiMatrix.innerHTML = coverage.map(([title, route], index) => `
    <article class="matrix-card ${index % 2 ? "gold" : component.accent}">
      <div>
        <span>${String(index + 1).padStart(2, "0")}</span>
        <h3>${escapeHtml(title)}</h3>
      </div>
      <ul><li><code>${escapeHtml(route)}</code></li></ul>
    </article>
  `).join("");
}

function renderComponentTwo() {
  const c2 = state.componentTwo || {};
  const metrics = c2.metrics || {};
  const prediction = c2.latest_prediction || {};
  els.c2TelemetryCount.textContent = metrics.telemetry_points || 0;
  els.c2PredictionCount.textContent = metrics.predictions || 0;
  els.c2LatestLabel.textContent = prediction.label ? prettify(prediction.label) : "None";
  els.c2LatestConfidence.textContent = `${Math.round(Number(prediction.confidence || 0) * 100)}% confidence`;
  els.c2RiskScore.textContent = `${Math.round(Number(prediction.sla_risk_score || 0) * 100)}%`;
  const latency = metrics.avg_mitigation_latency_ms;
  els.c2MitigationLatency.textContent = latency === null || latency === undefined ? "latency pending" : `${Number(latency).toFixed(1)} ms mitigation`;
  els.componentTwoPredictionJson.textContent = JSON.stringify({
    latest_prediction: prediction || null,
    latest_telemetry: c2.latest_telemetry || null,
    models: c2.models || {},
    platform: c2.platform || {}
  }, null, 2);
}

function renderComponentThree() {
  const c3 = state.componentThree || {};
  const metrics = c3.metrics || {};
  els.c3IntentCount.textContent = metrics.intents_received || 0;
  els.c3RuleCount.textContent = metrics.rules_generated || 0;
  const avgLatency = metrics.avg_translation_latency_ms;
  els.c3AvgLatency.textContent = avgLatency === null || avgLatency === undefined ? "0 ms" : `${Number(avgLatency).toFixed(2)} ms`;
  els.c3ContextScore.textContent = `${Math.round(Number(metrics.context_score || 0) * 100)}%`;
  els.componentThreeOutputJson.textContent = JSON.stringify({
    latest_intent: c3.latest_intent || null,
    latest_rule: c3.latest_rule || null,
    latest_context_update: c3.latest_context_update || null,
    active_rules: metrics.active_rules || 0,
    hosts: c3.hosts || {}
  }, null, 2);
}

function renderComponentFour() {
  const c4 = state.componentFour || {};
  const metrics = c4.metrics || {};
  els.c4SessionCount.textContent = metrics.sessions || 0;
  els.c4SessionRisk.textContent = `${metrics.suspicious_sessions || 0} suspicious`;
  els.c4QuarantineCount.textContent = metrics.quarantined_subjects || metrics.quarantined_sessions || 0;
  els.c4BlockedIocCount.textContent = metrics.blocked_iocs || 0;
  els.c4RuleCount.textContent = metrics.active_security_rules || 0;
  const latency = metrics.avg_mitigation_latency_ms;
  els.c4MitigationLatency.textContent = latency === null || latency === undefined ? "latency pending" : `${Number(latency).toFixed(2)} ms avg`;
  els.componentFourOutputJson.textContent = JSON.stringify({
    metrics,
    sessions: c4.sessions || [],
    active_rules: c4.active_rules || [],
    indicators: (c4.indicators || []).slice(0, 8),
    recent_flow_evaluations: c4.recent_flow_evaluations || []
  }, null, 2);
}

async function routeRequest() {
  const payload = {
    client_ip: valueOf("routeClientIp"),
    client_port: Number(valueOf("routeClientPort")),
    vip_port: Number(valueOf("routeVipPort")),
    request_size_kb: Number(valueOf("routeSize")),
    ip_proto: 6,
    priority: 100
  };
  try {
    const result = await apiRequest("/api/v1/component-1/route", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    if (!result.accepted) {
      showToast(result.error || "No eligible backend", true);
    } else {
      showToast(`Flow installed on ${result.backend.name}`);
      document.getElementById("routeClientPort").value = String(payload.client_port + 1);
    }
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function recomputePlan() {
  try {
    const result = await apiRequest("/api/v1/resource-plans/recompute", { method: "POST", body: "{}" });
    showToast(`GA plan recomputed with ${Object.keys(result.plan?.backend_weights || {}).length} weights`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function submitMetrics(event) {
  event.preventDefault();
  const backend = valueOf("metricBackend");
  const payload = {
    cpu_percent: Number(valueOf("metricCpu")),
    memory_percent: Number(valueOf("metricMemory")),
    bandwidth_percent: Number(valueOf("metricBandwidth")),
    latency_ms: Number(valueOf("metricLatency")),
    throughput_mbps: Number(valueOf("metricThroughput"))
  };
  try {
    await apiRequest(`/api/v1/component-1/backends/${encodeURIComponent(backend)}/metrics`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`${backend} metrics updated`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function runSimulation(event) {
  event.preventDefault();
  const faultBackend = valueOf("simulationFaultBackend");
  const payload = {
    requests: Number(valueOf("simulationRequests")),
    start_port: Number(valueOf("simulationStartPort")),
    vip_port: Number(valueOf("routeVipPort")) || 8000,
    request_size_kb: Number(valueOf("routeSize")) || 128,
    clients: ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"],
    recompute_after: true,
    inject_fault_backend: faultBackend || null
  };
  try {
    const result = await apiRequest("/api/v1/component-1/workload/simulate", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`Simulation routed ${result.routed}/${result.requests} requests`);
    document.getElementById("simulationStartPort").value = String(payload.start_port + payload.requests + 1);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function setBackendHealth(backend, healthy) {
  try {
    await apiRequest(`/api/v1/component-1/backends/${encodeURIComponent(backend)}/health`, {
      method: "POST",
      body: JSON.stringify({ healthy, reason: healthy ? "manual enable" : "manual fault" })
    });
    showToast(`${backend} marked ${healthy ? "healthy" : "offline"}`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function resetComponentOne() {
  try {
    await apiRequest("/api/v1/component-1/reset", { method: "POST", body: "{}" });
    showToast("Component 1 runtime reset");
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function runIntegratedModel() {
  const scenario = valueOf("integratedScenario") || "mixed";
  const payload = {
    scenario,
    workload_requests: 28,
    include_monitoring: true,
    include_intent: true,
    include_security: true
  };
  try {
    els.runIntegratedBtn.disabled = true;
    const result = await apiRequest("/api/v1/integrated/run", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    state.latestIntegratedRun = result;
    state.integratedRunCount += 1;
    els.integratedRunJson.textContent = JSON.stringify(result, null, 2);
    showToast(`Integrated ${prettify(scenario)} run completed`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.runIntegratedBtn.disabled = false;
  }
}

async function validatePlatformStack() {
  try {
    els.validatePlatformBtn.disabled = true;
    const result = await apiRequest("/api/v1/platform/validate");
    state.platformValidation = result;
    els.integratedRunJson.textContent = JSON.stringify(result, null, 2);
    const sdnMode = result.sdn_lab?.mode || "checked";
    showToast(`Platform validation: ${sdnMode}`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.validatePlatformBtn.disabled = false;
  }
}

async function submitComponentTwoTelemetry(event) {
  event.preventDefault();
  const observed = valueOf("c2ObservedLabel");
  const payload = {
    source: "component-2-frontend",
    active_flows: Number(valueOf("c2ActiveFlows")),
    packet_rate_per_sec: Number(valueOf("c2PacketRate")),
    byte_rate_per_sec: Number(valueOf("c2ByteRate")),
    max_link_utilization_ratio: Number(valueOf("c2LinkUtil")),
    controller_cpu_percent: Number(valueOf("c2Cpu")),
    controller_memory_percent: Number(valueOf("c2Memory")),
    packet_in_rate_per_sec: Number(valueOf("c2PacketIn")),
    observed_label: observed || null,
    top_talker_src_ip: "10.0.0.2",
    top_talker_dst_ip: "10.0.0.100"
  };
  try {
    const result = await apiRequest("/api/v1/component-2/telemetry", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`Prediction: ${prettify(result.component_2_prediction?.label || "unknown")}`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function fillComponentTwoScenario(name) {
  try {
    const result = await apiRequest(`/api/v1/component-2/scenarios/${encodeURIComponent(name)}`);
    const metrics = result.metrics || {};
    document.getElementById("c2ActiveFlows").value = metrics.active_flows ?? 0;
    document.getElementById("c2PacketRate").value = metrics.packet_rate_per_sec ?? 0;
    document.getElementById("c2ByteRate").value = metrics.byte_rate_per_sec ?? 0;
    document.getElementById("c2LinkUtil").value = metrics.max_link_utilization_ratio ?? 0;
    document.getElementById("c2Cpu").value = metrics.controller_cpu_percent ?? 0;
    document.getElementById("c2Memory").value = metrics.controller_memory_percent ?? 0;
    document.getElementById("c2PacketIn").value = metrics.packet_in_rate_per_sec ?? 0;
    document.getElementById("c2ObservedLabel").value = ["normal", "congestion", "ddos", "port_scan"].includes(name) ? name : "";
    els.componentTwoPredictionJson.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function trainComponentTwoModels() {
  try {
    const result = await apiRequest("/api/v1/component-2/models/train", {
      method: "POST",
      body: JSON.stringify({ samples_per_class: 500, seed: 42 })
    });
    showToast(`Models trained: ${(result.report.classifier_accuracy * 100).toFixed(1)}% accuracy`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function showComponentTwoPlatform() {
  try {
    const result = await apiRequest("/api/v1/component-2/platform");
    els.componentTwoPredictionJson.textContent = JSON.stringify(result, null, 2);
    showToast("Component 2 platform checked");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function submitComponentThreeIntent(event) {
  event.preventDefault();
  const expectedType = valueOf("c3ExpectedType");
  const payload = {
    intent: valueOf("c3IntentText"),
    priority: Number(valueOf("c3Priority")),
    src_ip: valueOf("c3SrcIp") || null,
    dst_ip: valueOf("c3DstIp") || null,
    proto: valueOf("c3Proto") || null,
    dst_port: Number(valueOf("c3DstPort")),
    expected_type: expectedType || null
  };
  try {
    const result = await apiRequest("/api/v1/component-3/intents", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    const type = result.component_3_translation?.classification?.type || "generic";
    showToast(`Intent translated as ${prettify(type)}`);
    els.componentThreeOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function submitComponentThreeContext(event) {
  event.preventDefault();
  const payload = {
    source: "component-3-frontend",
    threat: valueOf("c3Threat"),
    congestion: valueOf("c3Congestion"),
    load: valueOf("c3Load"),
    latency_ms: Number(valueOf("c3Latency")),
    bandwidth_utilization: Number(valueOf("c3Bandwidth")),
    resource_utilization: Number(valueOf("c3Resource")),
    time_context: valueOf("c3TimeContext"),
    policy_context: valueOf("c3PolicyContext")
  };
  try {
    const result = await apiRequest("/api/v1/component-3/context", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`Context adapted ${result.component_3_context?.adapted_rules || 0} rules`);
    els.componentThreeOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function fillComponentThreeScenario(name) {
  try {
    const result = await apiRequest(`/api/v1/component-3/scenarios/${encodeURIComponent(name)}`);
    const intent = result.intent_payload || {};
    const context = result.context_payload || {};
    document.getElementById("c3IntentText").value = intent.intent || "";
    document.getElementById("c3Priority").value = intent.priority ?? 1;
    document.getElementById("c3ExpectedType").value = intent.expected_type || "";
    document.getElementById("c3SrcIp").value = intent.src_ip || "";
    document.getElementById("c3DstIp").value = intent.dst_ip || "";
    document.getElementById("c3Proto").value = intent.proto || "tcp";
    document.getElementById("c3DstPort").value = intent.dst_port || 443;
    document.getElementById("c3Threat").value = context.threat || "low";
    document.getElementById("c3Congestion").value = context.congestion || "low";
    document.getElementById("c3Load").value = context.load || "normal";
    document.getElementById("c3Latency").value = context.latency_ms ?? 35;
    document.getElementById("c3Bandwidth").value = context.bandwidth_utilization ?? 0.25;
    document.getElementById("c3Resource").value = context.resource_utilization ?? 0.32;
    document.getElementById("c3TimeContext").value = context.time_context || "business_hours";
    document.getElementById("c3PolicyContext").value = context.policy_context || "standard";
    els.componentThreeOutputJson.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function showComponentThreePlatform() {
  try {
    const result = await apiRequest("/api/v1/component-3/platform");
    els.componentThreeOutputJson.textContent = JSON.stringify(result, null, 2);
    showToast("Component 3 platform checked");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function showComponentThreeHosts() {
  try {
    const result = await apiRequest("/api/v1/component-3/hosts");
    els.componentThreeOutputJson.textContent = JSON.stringify(result, null, 2);
    showToast(`${result.total_hosts || 0} hosts loaded`);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loginComponentFourSession() {
  const payload = {
    user_id: valueOf("c4UserId"),
    ip: valueOf("c4LoginIp"),
    password: valueOf("c4Password")
  };
  try {
    const result = await apiRequest("/api/v1/component-4/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    if (result.token) {
      document.getElementById("c4Token").value = result.token;
      showToast("Component 4 session created");
    } else {
      showToast(result.error || "Login failed", true);
    }
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function verifyComponentFourSession(event) {
  event.preventDefault();
  const payload = {
    token: valueOf("c4Token"),
    ip: valueOf("c4VerifyIp"),
    bytes_sent: Number(valueOf("c4BytesSent"))
  };
  try {
    const result = await apiRequest("/api/v1/component-4/auth/verify", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(result.allowed ? "Session allowed" : `Session blocked: ${result.reason || "risk"}`);
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function evaluateComponentFourSecurity(event) {
  event.preventDefault();
  const flowPayload = {
    src_ip: valueOf("c4SrcIp"),
    dst_ip: valueOf("c4DstIp"),
    dst_port: Number(valueOf("c4Port")),
    protocol: valueOf("c4Protocol")
  };
  const alertPayload = {
    src_ip: valueOf("c4Indicator"),
    signature: valueOf("c4Signature"),
    severity: Number(valueOf("c4Severity")),
    threat_type: valueOf("c4Signature")
  };
  try {
    const [flowResult, alertResult] = await Promise.all([
      apiRequest("/api/v1/component-4/segmentation/evaluate", {
        method: "POST",
        body: JSON.stringify(flowPayload)
      }),
      apiRequest("/api/v1/component-4/cti/alert", {
        method: "POST",
        body: JSON.stringify(alertPayload)
      })
    ]);
    showToast(`${flowResult.allowed ? "Allowed" : "Blocked"} flow, alert ${alertResult.should_block ? "blocked" : "observed"}`);
    els.componentFourOutputJson.textContent = JSON.stringify({ flowResult, alertResult }, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function enforceComponentFourSegmentation() {
  try {
    const result = await apiRequest("/api/v1/component-4/segmentation/enforce", {
      method: "POST",
      body: "{}"
    });
    showToast(`${result.count || 0} segmentation rules generated`);
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function fetchComponentFourCti() {
  try {
    const result = await apiRequest("/api/v1/component-4/cti/fetch", {
      method: "POST",
      body: "{}"
    });
    showToast(`${result.new_iocs || 0} CTI indicators added`);
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function blockComponentFourIoc() {
  const payload = {
    value: valueOf("c4Indicator"),
    reason: "manual CTI block from console"
  };
  try {
    const result = await apiRequest("/api/v1/component-4/cti/block", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`Blocked ${payload.value}`);
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function fillComponentFourScenario(name) {
  try {
    const result = await apiRequest(`/api/v1/component-4/scenarios/${encodeURIComponent(name)}`);
    if (result.flow) {
      document.getElementById("c4SrcIp").value = result.flow.src_ip || "10.0.0.1";
      document.getElementById("c4DstIp").value = result.flow.dst_ip || "10.0.0.12";
      document.getElementById("c4Port").value = result.flow.dst_port || 3306;
      document.getElementById("c4Protocol").value = result.flow.protocol || "tcp";
    }
    if (result.alert) {
      document.getElementById("c4Indicator").value = result.alert.src_ip || "";
      document.getElementById("c4Signature").value = result.alert.signature || "";
      document.getElementById("c4Severity").value = String(result.alert.severity || 1);
    }
    if (result.indicator) {
      document.getElementById("c4Indicator").value = result.indicator.value || "";
      document.getElementById("c4Signature").value = result.indicator.threat_type || "";
    }
    if (result.auth) {
      document.getElementById("c4UserId").value = result.auth.user_id || "admin";
      document.getElementById("c4LoginIp").value = result.auth.ip || "10.0.0.2";
      document.getElementById("c4Password").value = result.auth.password || "admin123";
      document.getElementById("c4VerifyIp").value = result.auth.verify_ip || result.auth.ip || "10.0.0.2";
      document.getElementById("c4BytesSent").value = result.auth.bytes_sent || 2048;
    }
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function showComponentFourPlatform() {
  try {
    const result = await apiRequest("/api/v1/component-4/platform");
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    showToast("Component 4 platform checked");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function showComponentFourRules() {
  try {
    const result = await apiRequest("/api/v1/component-4/rules");
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    showToast(`${result.active_rules?.length || 0} active security rules`);
  } catch (error) {
    showToast(error.message, true);
  }
}

function activateTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  document.querySelectorAll(".action-form").forEach((form) => {
    form.classList.toggle("active", form.dataset.pane === name);
  });
}

function fillMetricScenario(name) {
  const scenarios = {
    balanced: { metricCpu: 45, metricMemory: 42, metricBandwidth: 38, metricLatency: 55, metricThroughput: 310 },
    overload: { metricCpu: 92, metricMemory: 88, metricBandwidth: 84, metricLatency: 220, metricThroughput: 940 }
  };
  Object.entries(scenarios[name] || scenarios.balanced).forEach(([id, value]) => {
    document.getElementById(id).value = value;
  });
}

function getBackends() {
  return state.componentOne?.backends || [];
}

function getComponentCounts() {
  const snapshot = state.snapshot || {};
  return {
    "component-1": (state.componentOne?.events || []).length,
    "component-2": state.componentTwo?.metrics?.predictions || (snapshot.contexts || []).length,
    "component-3": state.componentThree?.metrics?.rules_generated || (snapshot.intents || []).length,
    "component-4": state.componentFour?.metrics?.active_security_rules || (snapshot.security_actions || []).length
  };
}

function getSelectedComponent() {
  return componentConfigs.find((component) => component.id === state.selectedComponentId) || componentConfigs[0];
}

function setApiStatus(mode, label) {
  els.apiStatus.className = `status-pill ${mode}`;
  els.apiStatus.innerHTML = `<span class="status-dot"></span>${escapeHtml(label)}`;
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("visible");
  window.setTimeout(() => {
    els.toast.classList.remove("visible");
  }, 2800);
}

function metricBadge(label, value) {
  return `<span><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`;
}

function percent(value) {
  if (value === null || value === undefined) {
    return "0%";
  }
  return `${Math.round(Number(value) * 100)}%`;
}

function valueOf(id) {
  return document.getElementById(id).value.trim();
}

function lastItem(items = []) {
  return items.length ? items[items.length - 1] : null;
}

function prettify(value = "") {
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function shortKind(value = "") {
  const text = String(value).replace(/_/g, " ");
  return text.split(" ").map((part) => part[0] || "").join("").slice(0, 4).toUpperCase();
}

function formatTime(ts) {
  if (!ts) {
    return "pending";
  }
  return new Date(Number(ts) * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
