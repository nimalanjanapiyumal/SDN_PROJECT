import { componentConfigs } from "../../components/index.js";

const state = {
  selectedComponentId: componentConfigs[0].id,
  snapshot: null,
  componentOne: null,
  componentTwo: null,
  componentThree: null,
  componentFour: null,
  integrated: null,
  sdnRuntime: null,
  automation: null,
  auth: null,
  authToken: window.localStorage.getItem("adaptiveOperatorToken") || "",
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
    "operatorUser",
    "operatorPass",
    "operatorLoginBtn",
    "operatorLogoutBtn",
    "authStatus",
    "integratedScenario",
    "automationInterval",
    "startAutomationBtn",
    "stopAutomationBtn",
    "runIntegratedBtn",
    "validatePlatformBtn",
    "sdnLabScenario",
    "sdnLabDuration",
    "sdnLinkMode",
    "startSdnLabBtn",
    "stopSdnLabBtn",
    "validateSdnBtn",
    "startMonitoringStackBtn",
    "stopMonitoringStackBtn",
    "sdnRuntimeSummary",
    "sdnTopologyView",
    "sdnControllerWindow",
    "sdnOpenflowList",
    "sdnMonitoringViews",
    "sdnCommandList",
    "sdnRuntimeJson",
    "combinedHealth",
    "combinedRuns",
    "combinedLatency",
    "monitoringReady",
    "sdnReady",
    "automationState",
    "automationCycles",
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
    "componentTwoOutcomeGrid",
    "componentTwoLinkGrid",
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
    "componentFourOutputJson",
    "componentFourRuleStatus",
    "componentFourRuleList",
    "componentFourAttackBanner",
    "componentFourIncidentList",
    "componentFourSubjectList",
    "componentFourServerAnalysis",
    "componentFourObjectiveGrid",
    "componentFourGraphGrid",
    "componentFourLinuxGrid",
    "componentFourLinkGrid"
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
  els.apiBase.textContent = window.location.origin;
}

function bindEvents() {
  els.refreshBtn.addEventListener("click", () => refreshAll());
  els.operatorLoginBtn.addEventListener("click", loginOperator);
  els.operatorLogoutBtn.addEventListener("click", logoutOperator);
  els.startAutomationBtn.addEventListener("click", startSystemAutomation);
  els.stopAutomationBtn.addEventListener("click", stopSystemAutomation);
  els.runIntegratedBtn.addEventListener("click", runIntegratedModel);
  els.validatePlatformBtn.addEventListener("click", validatePlatformStack);
  els.startSdnLabBtn.addEventListener("click", startSdnLab);
  els.stopSdnLabBtn.addEventListener("click", stopSdnLab);
  els.validateSdnBtn.addEventListener("click", validateSdnRuntime);
  els.startMonitoringStackBtn.addEventListener("click", startMonitoringStack);
  els.stopMonitoringStackBtn.addEventListener("click", stopMonitoringStack);
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
  els.componentFourSubjectList.addEventListener("click", handleComponentFourSubjectAction);
  els.sdnMonitoringViews.addEventListener("click", handleOpenRuntimeLink);
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
    const [health, snapshot, componentOne, componentTwo, componentThree, componentFour, integrated, automation, auth] = await Promise.all([
      apiRequest("/healthz"),
      apiRequest("/api/v1/state"),
      apiRequest("/api/v1/component-1/status"),
      apiRequest("/api/v1/component-2/status"),
      apiRequest("/api/v1/component-3/status"),
      apiRequest("/api/v1/component-4/status"),
      apiRequest("/api/v1/integrated/status"),
      apiRequest("/api/v1/automation/status"),
      apiRequest("/api/v1/auth/status")
    ]);
    state.health = health;
    state.snapshot = snapshot;
    state.componentOne = componentOne;
    state.componentTwo = componentTwo;
    state.componentThree = componentThree;
    state.componentFour = componentFour;
    state.integrated = integrated;
    state.sdnRuntime = integrated?.sdn_runtime || null;
    state.automation = automation;
    state.auth = auth;
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

async function loginOperator() {
  const payload = {
    username: valueOf("operatorUser"),
    password: valueOf("operatorPass")
  };
  try {
    const result = await apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {}
    });
    if (!result.authenticated || !result.token) {
      showToast(result.error || "Login failed", true);
      return;
    }
    state.authToken = result.token;
    window.localStorage.setItem("adaptiveOperatorToken", result.token);
    showToast("Operator login successful");
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function logoutOperator() {
  try {
    await apiRequest("/api/v1/auth/logout", {
      method: "POST",
      body: "{}"
    });
  } catch (error) {
    // Best effort logout; clear local token even if the server session is already gone.
  } finally {
    state.authToken = "";
    state.auth = { authenticated: false };
    window.localStorage.removeItem("adaptiveOperatorToken");
    renderAuthState();
    showToast("Operator logged out");
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(state.authToken ? { "X-Operator-Token": state.authToken } : {}),
      ...(options.headers || {})
    },
    ...options
  });
  if (!response.ok) {
    const body = await response.text();
    if (response.status === 401) {
      state.auth = { authenticated: false };
      state.authToken = "";
      window.localStorage.removeItem("adaptiveOperatorToken");
      renderAuthState();
    }
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
  renderAuthState();
  renderSdnRuntime();
  renderComponentPanel();
  renderComponentNav();
  renderWorkspaceVisibility();
}

function renderAuthState() {
  const auth = state.auth || { authenticated: false };
  const authenticated = Boolean(auth.authenticated);
  const automation = state.automation || {};
  const lab = state.sdnRuntime?.lab || {};
  els.authStatus.className = `status-pill ${authenticated ? "online" : "offline"}`;
  els.authStatus.innerHTML = `<span class="status-dot"></span>${escapeHtml(authenticated ? `Operator ${auth.username || "admin"}` : "Locked")}`;
  els.operatorLoginBtn.disabled = authenticated;
  els.operatorLogoutBtn.disabled = !authenticated;
  els.operatorUser.disabled = authenticated;
  els.operatorPass.disabled = authenticated;
  els.startAutomationBtn.disabled = !authenticated || Boolean(automation.running);
  els.stopAutomationBtn.disabled = !authenticated || !automation.running;
  els.runIntegratedBtn.disabled = !authenticated;
  els.startSdnLabBtn.disabled = !authenticated;
  els.stopSdnLabBtn.disabled = !authenticated || !lab.running;
  els.startMonitoringStackBtn.disabled = !authenticated;
  els.stopMonitoringStackBtn.disabled = !authenticated;
  els.componentFourEnforceSegBtn.disabled = !authenticated;
  els.componentFourFetchCtiBtn.disabled = !authenticated;
  els.componentFourBlockIocBtn.disabled = !authenticated;
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
  const sdnRuntime = state.sdnRuntime || integrated.sdn_runtime || {};
  const automation = state.automation || integrated.automation || {};
  const health = integrated.operator_health || {};
  const readiness = integrated.readiness || {};
  const runs = integrated.integrated_runs || {};
  const monitoringReady = readiness.monitoring?.files_ready;
  const sdnFilesReady = readiness.sdn_lab?.files_ready;
  const realSdnReady = sdnRuntime.lab?.controller_probe?.reachable || readiness.sdn_lab?.real_dataplane_ready;
  const latest = state.latestIntegratedRun || runs.latest || automation.last_result;

  els.combinedHealth.textContent = health.automatic_pipeline_ready ? "Ready" : "Check";
  state.integratedRunCount = Math.max(state.integratedRunCount || 0, Number(runs.count || 0));
  els.combinedRuns.textContent = state.integratedRunCount || 0;
  els.combinedLatency.textContent = latest?.latency_ms ? `${Number(latest.latency_ms).toFixed(1)} ms latest` : "latency pending";
  els.monitoringReady.textContent = monitoringReady ? "Ready" : "Check";
  els.sdnReady.textContent = realSdnReady ? "Live" : (sdnFilesReady ? "Prepared" : "Check");
  els.automationState.textContent = automation.running ? "Running" : "Stopped";
  els.automationCycles.textContent = `${Number(automation.executed_cycles || 0)} cycles`;
  els.startAutomationBtn.disabled = Boolean(automation.running);
  els.stopAutomationBtn.disabled = !automation.running;
  if (latest) {
    els.integratedRunJson.textContent = JSON.stringify(latest, null, 2);
  } else if (!state.platformValidation) {
    els.integratedRunJson.textContent = JSON.stringify({
      automatic_pipeline: health.automatic_pipeline_ready || false,
      observability_files_ready: monitoringReady || false,
      sdn_lab_files_ready: sdnFilesReady || false,
      real_sdn_runtime_ready: realSdnReady || false
    }, null, 2);
  }
}

function renderSdnRuntime() {
  const runtime = state.sdnRuntime || state.integrated?.sdn_runtime || {};
  const lab = runtime.lab || {};
  const monitoring = runtime.monitoring || {};
  const openflow = runtime.openflow || {};
  const topology = runtime.topology || {};
  const environment = runtime.environment || {};
  const supported = Boolean(lab.supported);

  if (!els.sdnRuntimeSummary) {
    return;
  }

  els.sdnRuntimeSummary.innerHTML = `
    <article class="sdn-status-card ${lab.running ? "live" : "idle"}">
      <span>Lab</span>
      <strong>${lab.running ? "Running" : (supported ? "Ready" : "Linux only")}</strong>
      <em>${lab.controller_probe?.reachable ? "controller on 6653" : "controller offline"}</em>
    </article>
    <article class="sdn-status-card ${monitoring.prometheus?.reachable ? "live" : "idle"}">
      <span>Prometheus</span>
      <strong>${monitoring.prometheus?.reachable ? "Live" : "Down"}</strong>
      <em>${monitoring.prometheus?.latency_ms ? `${Number(monitoring.prometheus.latency_ms).toFixed(0)} ms` : "127.0.0.1:9090"}</em>
    </article>
    <article class="sdn-status-card ${monitoring.grafana?.reachable ? "live" : "idle"}">
      <span>Grafana</span>
      <strong>${monitoring.grafana?.reachable ? "Live" : "Down"}</strong>
      <em>${monitoring.grafana?.latency_ms ? `${Number(monitoring.grafana.latency_ms).toFixed(0)} ms` : "127.0.0.1:3000"}</em>
    </article>
    <article class="sdn-status-card ${openflow.total_rules ? "live" : "idle"}">
      <span>OpenFlow</span>
      <strong>${openflow.total_rules || 0} rules</strong>
      <em>${environment.platform || "runtime"} / ${environment.linux_runtime ? "Linux" : "non-Linux"}</em>
    </article>
  `;

  els.sdnTopologyView.innerHTML = renderSdnTopology(topology);
  els.sdnControllerWindow.innerHTML = renderSdnControllerWindow(runtime);
  els.sdnOpenflowList.innerHTML = renderSdnOpenflow(openflow);
  els.sdnMonitoringViews.innerHTML = renderSdnMonitoringViews(monitoring.views || []);
  els.sdnCommandList.innerHTML = renderSdnCommands(runtime.commands || []);
  els.sdnRuntimeJson.textContent = JSON.stringify(runtime, null, 2);
}

function renderSdnTopology(topology) {
  const controller = topology.controller || {};
  const switches = topology.switches || [];
  const hosts = topology.hosts || [];
  const services = topology.services || [];
  const monitoringNodes = topology.monitoring_nodes || [];
  return `
    <div class="sdn-topology-stage">
      <div class="sdn-topology-row controller-row">
        ${renderSdnNode(controller.name || "Ryu", controller.state || "idle", `${controller.rules || 0} rules`)}
      </div>
      <div class="sdn-topology-row switch-row">
        ${switches.map((item) => renderSdnNode(item.name, item.state, `${item.rules || 0} rules`)).join("")}
      </div>
      <div class="sdn-topology-row host-row">
        ${hosts.map((item) => renderSdnNode(item.name, "live", item.ip)).join("")}
      </div>
      <div class="sdn-topology-row service-row">
        ${services.map((item) => renderSdnNode(item.name, item.state || "idle", item.ip || item.note || "")).join("")}
      </div>
      <div class="sdn-topology-row monitor-row">
        ${monitoringNodes.map((item) => renderSdnNode(item.name, item.state || "idle", item.url?.replace("http://", "") || "")).join("")}
      </div>
    </div>
  `;
}

function renderSdnNode(title, stateName, detail) {
  return `
    <article class="sdn-node ${escapeHtml(String(stateName || "idle"))}">
      <strong>${escapeHtml(title || "node")}</strong>
      <span>${escapeHtml(detail || "")}</span>
    </article>
  `;
}

function renderSdnOpenflow(openflow) {
  const counts = openflow.component_counts || {};
  const rules = openflow.rules || [];
  return `
    <div class="sdn-openflow-summary">
      <span>C1 ${counts.component_1 || 0}</span>
      <span>C3 ${counts.component_3 || 0}</span>
      <span>C4 ${counts.component_4 || 0}</span>
    </div>
    <div class="sdn-openflow-rule-list">
      ${rules.length ? rules.map((rule) => `
        <article class="sdn-openflow-rule">
          <div>
            <strong>${escapeHtml(rule.id || rule.action || "rule")}</strong>
            <span>${escapeHtml(prettify(rule.component || "component"))} | ${escapeHtml(rule.switch || "fabric")}</span>
          </div>
          <div class="sdn-openflow-meta">
            <span>${escapeHtml(prettify(rule.action || "forward"))}</span>
            <span>${escapeHtml(rule.summary || "")}</span>
          </div>
        </article>
      `).join("") : `<p class="empty">No OpenFlow-compatible rules are active yet.</p>`}
    </div>
  `;
}

function renderSdnControllerWindow(runtime) {
  const lab = runtime.lab || {};
  const controller = lab.controller_window || {};
  const topology = runtime.topology || {};
  const openflow = runtime.openflow || {};
  const switches = topology.switches || [];
  const connected = switches.filter((item) => item.state === "live");
  const logs = controller.recent_logs || [];
  const lastError = controller.last_error || lab.last_error || "";
  return `
    <div class="sdn-controller-summary">
      <span>Status: ${escapeHtml(prettify(controller.status || "offline"))}</span>
      <span>Port: ${escapeHtml(String(controller.port || 6653))}</span>
      <span>Switches: ${connected.length}/${switches.length}</span>
      <span>Rules: ${escapeHtml(String(openflow.total_rules || 0))}</span>
    </div>
    <div class="sdn-controller-links">
      ${switches.map((item) => `<span class="controller-link ${escapeHtml(item.state || "idle")}">${escapeHtml(item.name)} | ${item.rules || 0} rules</span>`).join("")}
    </div>
    ${lastError ? `<div class="sdn-controller-alert">${escapeHtml(lastError)}</div>` : ""}
    ${logs.length ? `<div class="sdn-controller-log">${logs.map((line) => `<div>${escapeHtml(line)}</div>`).join("")}</div>` : `<p class="empty">Controller log will appear when Ryu starts.</p>`}
  `;
}

function renderSdnMonitoringViews(views) {
  if (!views.length) {
    return `<p class="empty">No monitoring views configured.</p>`;
  }
  return views.map((view) => `
    <article class="sdn-view-card ${view.reachable ? "live" : "idle"}">
      <div>
        <strong>${escapeHtml(view.name)}</strong>
        <span>${escapeHtml(view.status || "unknown")}</span>
      </div>
      <div class="button-row">
        <button class="mini-button" type="button" data-open-url="${escapeHtml(view.url || "")}">Open</button>
      </div>
    </article>
  `).join("");
}

function renderSdnCommands(commands) {
  if (!commands.length) {
    return `<p class="empty">No runtime commands available.</p>`;
  }
  return commands.map((item) => `
    <article class="sdn-command-card">
      <strong>${escapeHtml(item.name || "Command")}</strong>
      <span>${escapeHtml(item.description || "")}</span>
      <code>${escapeHtml(item.command || "")}</code>
    </article>
  `).join("");
}

function renderComponentPanel() {
  const component = getSelectedComponent();
  const c1 = state.componentOne || {};
  const metricRows = getComponentMetricRows(component.id);
  const latestByComponent = {
    "component-1": lastItem(c1.events || []),
    "component-2": lastItem((state.snapshot || {}).contexts || []),
    "component-3": state.componentThree?.latest_intent || lastItem((state.snapshot || {}).intents || []),
    "component-4": state.componentFour?.recent_enforcement_events?.slice(-1)[0] || lastItem((state.snapshot || {}).security_actions || [])
  };
  const latest = latestByComponent[component.id] || {};

  els.componentPanel.innerHTML = `
    <div class="component-summary ${component.accent}">
      <span>${component.number}</span>
      <div>
        <p class="eyebrow">${escapeHtml(component.owner)}</p>
        <h2>${escapeHtml(component.title)}</h2>
      </div>
    </div>
    <div class="summary-metrics">
      ${metricRows.map(([label, value]) => `
        <article>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(String(value))}</strong>
        </article>
      `).join("")}
    </div>
    <details class="payload-drawer compact">
      <summary>Latest Payload</summary>
      <pre>${escapeHtml(JSON.stringify(latest, null, 2))}</pre>
    </details>
  `;
}

function getComponentMetricRows(componentId) {
  const c1 = state.componentOne || {};
  const c2 = state.componentTwo || {};
  const c3 = state.componentThree || {};
  const c4 = state.componentFour || {};
  const rows = {
    "component-1": [
      ["Routes", c1.metrics?.rr_decisions || 0],
      ["GA Runs", c1.metrics?.ga_runs || 0],
      ["Backends", `${c1.metrics?.healthy_backends || 0}/${c1.metrics?.total_backends || 0}`]
    ],
    "component-2": [
      ["Telemetry", c2.metrics?.telemetry_points || 0],
      ["Predictions", c2.metrics?.predictions || 0],
      ["Risk", `${Math.round(Number(c2.latest_prediction?.sla_risk_score || 0) * 100)}%`]
    ],
    "component-3": [
      ["Intents", c3.metrics?.intents_received || 0],
      ["Rules", c3.metrics?.rules_generated || 0],
      ["Context", `${Math.round(Number(c3.metrics?.context_score || 0) * 100)}%`]
    ],
    "component-4": [
      ["Sessions", c4.metrics?.sessions || 0],
      ["Rules", c4.metrics?.active_security_rules || 0],
      ["Blocked", c4.metrics?.blocked_iocs || 0]
    ]
  };
  return rows[componentId] || [];
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
    const securityAction = backend.security_action ? prettify(backend.security_action) : null;
    const securityNote = backend.security_reason || null;
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
          ${securityAction ? metricBadge("SEC", securityAction) : ""}
        </div>
        ${securityNote ? `<div class="backend-security-note"><strong>Security:</strong> ${escapeHtml(securityNote)}${backend.security_expires_at ? ` <span>Until ${escapeHtml(formatTime(backend.security_expires_at))}</span>` : ""}</div>` : ""}
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
  const outcomes = c2.expected_outcomes || {};
  const platform = c2.platform || {};
  els.c2TelemetryCount.textContent = metrics.telemetry_points || 0;
  els.c2PredictionCount.textContent = metrics.predictions || 0;
  els.c2LatestLabel.textContent = prediction.label ? prettify(prediction.label) : "None";
  els.c2LatestConfidence.textContent = `${Math.round(Number(prediction.confidence || 0) * 100)}% confidence`;
  els.c2RiskScore.textContent = `${Math.round(Number(prediction.sla_risk_score || 0) * 100)}%`;
  const latency = metrics.avg_mitigation_latency_ms;
  els.c2MitigationLatency.textContent = latency === null || latency === undefined ? "latency pending" : `${Number(latency).toFixed(1)} ms mitigation`;
  els.componentTwoOutcomeGrid.innerHTML = renderComponentTwoOutcomes(outcomes);
  els.componentTwoLinkGrid.innerHTML = renderComponentTwoLinks(platform);
  els.componentTwoPredictionJson.textContent = JSON.stringify({
    latest_prediction: prediction || null,
    latest_telemetry: c2.latest_telemetry || null,
    models: c2.models || {},
    expected_outcomes: outcomes,
    platform
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
  const objectives = c4.objectives || {};
  const functionalRequirements = c4.functional_requirements || {};
  const graphs = c4.graphs || {};
  const platform = c4.platform || {};
  const attackView = c4.attack_view || {};
  const incidents = c4.incident_feed || [];
  const subjects = c4.available_subjects || [];
  const analyses = c4.ip_security_analysis || [];
  const recentRules = c4.recent_rules || [];
  const latestRuleMessage = c4.latest_rule_message || "";
  els.c4SessionCount.textContent = metrics.sessions || 0;
  els.c4SessionRisk.textContent = `${metrics.suspicious_sessions || 0} suspicious`;
  els.c4QuarantineCount.textContent = metrics.temporary_blocks || metrics.quarantined_subjects || metrics.quarantined_sessions || 0;
  els.c4BlockedIocCount.textContent = metrics.blocked_iocs || 0;
  els.c4RuleCount.textContent = metrics.active_security_rules || 0;
  const latency = metrics.avg_mitigation_latency_ms;
  els.c4MitigationLatency.textContent = latency === null || latency === undefined ? "latency pending" : `${Number(latency).toFixed(2)} ms avg`;
  els.componentFourAttackBanner.innerHTML = renderComponentFourAttackBanner(attackView);
  els.componentFourAttackBanner.className = `attack-banner ${escapeHtml(String(attackView.status || "monitoring"))}`;
  els.componentFourIncidentList.innerHTML = renderComponentFourIncidentList(incidents);
  els.componentFourSubjectList.innerHTML = renderComponentFourSubjectList(subjects, subjects);
  els.componentFourRuleStatus.innerHTML = renderComponentFourRuleStatus(latestRuleMessage);
  els.componentFourRuleList.innerHTML = renderComponentFourRuleList(recentRules);
  els.componentFourServerAnalysis.innerHTML = renderComponentFourServerAnalysis(analyses, state.componentOne?.backends || []);
  els.componentFourObjectiveGrid.innerHTML = renderComponentFourObjectives(objectives, functionalRequirements);
  els.componentFourGraphGrid.innerHTML = renderComponentFourGraphs(graphs);
  els.componentFourLinuxGrid.innerHTML = renderComponentFourLinux(platform);
  els.componentFourLinkGrid.innerHTML = renderComponentFourLinks(platform);
  els.componentFourOutputJson.textContent = JSON.stringify({
    metrics,
    objectives,
    functional_requirements: functionalRequirements,
    graphs,
    benchmark: c4.benchmark || {},
    attack_view: attackView,
    incident_feed: incidents,
    latest_rule_message: latestRuleMessage,
    available_subjects: subjects,
    ip_security_analysis: analyses,
    platform,
    sessions: c4.sessions || [],
    active_rules: c4.active_rules || [],
    recent_rules: recentRules,
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

async function startSdnLab() {
  const payload = {
    scenario: valueOf("sdnLabScenario") || "mixed",
    duration_sec: Number(valueOf("sdnLabDuration")) || 90,
    interactive: false,
    link_mode: valueOf("sdnLinkMode") || "basic",
    start_monitoring: true
  };
  try {
    els.startSdnLabBtn.disabled = true;
    const result = await apiRequest("/api/v1/sdn/start", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    state.sdnRuntime = result.runtime || null;
    const action = result.action || {};
    showToast(action.launched ? `SDN lab started: ${prettify(payload.scenario)}` : (action.reason || action.status || "Manual Linux runtime required"));
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.startSdnLabBtn.disabled = false;
  }
}

async function stopSdnLab() {
  try {
    els.stopSdnLabBtn.disabled = true;
    const result = await apiRequest("/api/v1/sdn/stop", {
      method: "POST",
      body: "{}"
    });
    state.sdnRuntime = result.runtime || null;
    showToast(result.action?.stopped ? "SDN lab stopped" : "SDN lab is not running");
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.stopSdnLabBtn.disabled = false;
  }
}

async function validateSdnRuntime() {
  try {
    els.validateSdnBtn.disabled = true;
    const result = await apiRequest("/api/v1/sdn/status");
    state.sdnRuntime = result;
    els.sdnRuntimeJson.textContent = JSON.stringify(result, null, 2);
    showToast(result.lab?.controller_probe?.reachable ? "SDN controller reachable" : "SDN runtime checked");
    renderSdnRuntime();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.validateSdnBtn.disabled = false;
  }
}

async function startMonitoringStack() {
  try {
    els.startMonitoringStackBtn.disabled = true;
    const result = await apiRequest("/api/v1/monitoring/start", {
      method: "POST",
      body: JSON.stringify({ start_prometheus: true, start_grafana: true })
    });
    state.sdnRuntime = result.runtime || null;
    showToast(result.action?.started ? "Prometheus and Grafana started" : (result.action?.reason || result.action?.status || "Monitoring start checked"));
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.startMonitoringStackBtn.disabled = false;
  }
}

async function stopMonitoringStack() {
  try {
    els.stopMonitoringStackBtn.disabled = true;
    const result = await apiRequest("/api/v1/monitoring/stop", {
      method: "POST",
      body: "{}"
    });
    state.sdnRuntime = result.runtime || null;
    showToast(result.action?.stopped ? "Monitoring stopped" : (result.action?.reason || result.action?.status || "Monitoring stop checked"));
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.stopMonitoringStackBtn.disabled = false;
  }
}

async function startSystemAutomation() {
  const preferredScenario = valueOf("integratedScenario") || "mixed";
  const intervalSec = Number(valueOf("automationInterval")) || 20;
  const payload = {
    strategy: preferredScenario === "mixed" ? "adaptive" : "cycle",
    preferred_scenario: preferredScenario,
    scenario_sequence: preferredScenario === "mixed" ? ["normal", "congestion", "mixed", "ddos", "port_scan"] : [preferredScenario],
    interval_sec: intervalSec,
    workload_requests: 24,
    include_monitoring: true,
    include_intent: true,
    include_security: true,
    reset_on_start: false
  };
  try {
    els.startAutomationBtn.disabled = true;
    const result = await apiRequest("/api/v1/automation/start", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    state.automation = result;
    showToast(`Automation started at ${intervalSec}s`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function stopSystemAutomation() {
  try {
    els.stopAutomationBtn.disabled = true;
    const result = await apiRequest("/api/v1/automation/stop", {
      method: "POST",
      body: "{}"
    });
    state.automation = result;
    showToast("Automation stopped");
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
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
    const createdRule = extractSecurityRule(alertResult) || extractSecurityRule(flowResult);
    showToast(createdRule ? `Rule added: ${prettify(createdRule.action)} ${createdRule.subject}` : `${flowResult.allowed ? "Allowed" : "Blocked"} flow, alert ${alertResult.should_block ? "blocked" : "observed"}`);
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
    const createdRule = extractSecurityRule(result);
    showToast(createdRule ? `Rule added: ${prettify(createdRule.action)} ${createdRule.subject}` : `Blocked ${payload.value}`);
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

async function handleComponentFourSubjectAction(event) {
  const button = event.target.closest("[data-c4-subject][data-c4-action]");
  if (!button) {
    return;
  }
  const row = button.closest(".subject-row");
  const subject = button.dataset.c4Subject;
  const action = button.dataset.c4Action;
  const targets = action === "allow"
    ? Array.from((row?.querySelector(`[data-c4-targets-for="${subject}"]`) || { selectedOptions: [] }).selectedOptions || []).map((option) => option.value)
    : [];
  if (action === "allow" && !targets.length) {
    showToast("Select at least one server for this host allow rule", true);
    return;
  }
  const payload = {
    source: "component-4-gui",
    subject,
    action,
    severity: action === "allow" ? 2 : 4,
    reason: action === "allow"
      ? "manual micro-segmentation allowlist from GUI"
      : (action === "temporary_block" ? "temporary anomaly block from GUI" : "manual micro-segmentation deny from GUI"),
    duration_sec: action === "temporary_block" ? 300 : null,
    targets
  };
  try {
    const result = await apiRequest("/api/v1/component-4/access", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    const createdRule = extractSecurityRule(result);
    showToast(createdRule ? `Rule added: ${prettify(createdRule.action)} ${createdRule.subject}` : `${prettify(action)} applied to ${subject}`);
    els.componentFourOutputJson.textContent = JSON.stringify(result, null, 2);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

function handleOpenRuntimeLink(event) {
  const button = event.target.closest("[data-open-url]");
  if (!button) {
    return;
  }
  const url = button.dataset.openUrl;
  if (url) {
    window.open(url, "_blank", "noopener");
  }
}

function extractSecurityRule(result) {
  return result?.component_4_enforcement?.component_4_enforcement?.rule
    || result?.component_4_enforcement?.rule
    || result?.rule
    || null;
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

function renderComponentTwoOutcomes(outcomes) {
  const items = Object.values(outcomes || {});
  if (!items.length) {
    return `<p class="empty">No outcome data yet.</p>`;
  }
  return items.map((item) => {
    const metric = formatComponentTwoOutcomeMetric(item.metric, item.metric_label);
    return `
      <article class="outcome-card">
        <div class="outcome-top">
          <strong>${escapeHtml(item.title || "Outcome")}</strong>
          <span class="pill ${escapeHtml(String(item.status || "ready"))}">${escapeHtml(prettify(item.status || "ready"))}</span>
        </div>
        <b>${escapeHtml(metric)}</b>
        <p>${escapeHtml(item.detail || "")}</p>
      </article>
    `;
  }).join("");
}

function renderComponentTwoLinks(platform) {
  const endpoints = platform.monitoring_endpoints || [];
  const tools = platform.software_tools || [];
  const hardware = platform.hardware_requirements || {};
  return `
    <article class="resource-card">
      <div class="resource-head">
        <strong>Servers</strong>
        <span>${endpoints.length}</span>
      </div>
      <div class="resource-list">
        ${endpoints.length ? endpoints.map((item) => `
          <a class="resource-link" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noreferrer">
            <span>${escapeHtml(item.name || "Endpoint")}</span>
            <em>${escapeHtml(item.status || item.category || "link")}</em>
          </a>
        `).join("") : `<p class="empty">No local endpoints found.</p>`}
      </div>
    </article>
    <article class="resource-card">
      <div class="resource-head">
        <strong>Platforms</strong>
        <span>${tools.length}</span>
      </div>
      <div class="resource-list">
        ${tools.length ? tools.map((tool) => `
          <a class="resource-link" href="${escapeHtml(tool.docs_url || "#")}" target="_blank" rel="noreferrer">
            <span>${escapeHtml(tool.name || "Tool")}</span>
            <em>${escapeHtml(`${tool.purpose || "Platform"} | ${tool.installed ? "installed" : (tool.configured ? "files ready" : "not installed")}`)}</em>
          </a>
        `).join("") : `<p class="empty">No platform references found.</p>`}
      </div>
    </article>
    <article class="resource-card">
      <div class="resource-head">
        <strong>Hardware</strong>
        <span>Spec</span>
      </div>
      <div class="resource-spec">
        <span><b>CPU</b>${escapeHtml(hardware.cpu || "n/a")}</span>
        <span><b>Memory</b>${escapeHtml(hardware.memory || "n/a")}</span>
        <span><b>Storage</b>${escapeHtml(hardware.storage || "n/a")}</span>
      </div>
    </article>
  `;
}

function formatComponentTwoOutcomeMetric(value, label) {
  if (value === null || value === undefined) {
    return label ? `Pending ${label}` : "Pending";
  }
  if (typeof value === "number") {
    if ((label || "").includes("ms")) {
      return `${Number(value).toFixed(1)} ms`;
    }
    return `${Number(value).toLocaleString()} ${label || ""}`.trim();
  }
  return `${value} ${label || ""}`.trim();
}

function renderComponentFourObjectives(objectives, functionalRequirements) {
  const cards = [
    ...Object.values(objectives || {}).map((item) => ({ ...item, kind: "Objective" })),
    ...Object.values(functionalRequirements || {}).map((item) => ({ ...item, kind: "Function" }))
  ];
  if (!cards.length) {
    return `<p class="empty">No objective data yet.</p>`;
  }
  return cards.map((item) => `
    <article class="outcome-card">
      <div class="outcome-top">
        <strong>${escapeHtml(item.title || item.kind || "Item")}</strong>
        <span class="pill ${escapeHtml(String(item.status || "ready"))}">${escapeHtml(item.kind || "Item")}</span>
      </div>
      <b>${escapeHtml(formatComponentTwoOutcomeMetric(item.metric, item.metric_label))}</b>
      <p>${escapeHtml(item.detail || "")}</p>
    </article>
  `).join("");
}

function renderComponentFourGraphs(graphs) {
  const charts = Object.values(graphs || {});
  if (!charts.length) {
    return `<p class="empty">No graph data yet.</p>`;
  }
  return charts.map((chart) => renderBarChartCard(chart)).join("");
}

function renderBarChartCard(chart) {
  const items = chart.items || [];
  const maxValue = Math.max(...items.map((item) => Number(item.value || 0)), 1);
  return `
    <article class="chart-card">
      <div class="resource-head">
        <strong>${escapeHtml(chart.title || "Chart")}</strong>
        <span>${escapeHtml(chart.subtitle || "")}</span>
      </div>
      <div class="chart-bars">
        ${items.map((item) => {
          const value = Number(item.value || 0);
          const width = Math.max(4, Math.round((value / maxValue) * 100));
          return `
            <div class="chart-bar-row">
              <div class="chart-bar-meta">
                <span class="chart-bar-label">${escapeHtml(item.label || "Item")}</span>
                <strong class="chart-bar-value">${escapeHtml(formatChartValue(value, item.suffix))}</strong>
              </div>
              <div class="chart-bar-track">
                <span class="chart-bar-fill" style="width: ${width}%; background: ${escapeHtml(item.color || "#0f9f8e")};"></span>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </article>
  `;
}

function renderComponentFourLinux(platform) {
  const runtime = platform.linux_runtime || {};
  const features = runtime.features || [];
  if (!features.length) {
    return `<p class="empty">No Linux runtime data yet.</p>`;
  }
  return `
    <article class="resource-card">
      <div class="resource-head">
        <strong>${escapeHtml(runtime.preferred_runtime || "Linux runtime")}</strong>
        <span>${escapeHtml(runtime.current_platform || "unknown")}</span>
      </div>
      <div class="resource-list">
        ${features.map((feature) => `
          <div class="resource-link static">
            <span>${escapeHtml(feature.name || "Feature")}</span>
            <em>${escapeHtml(`${feature.available ? "available" : "not installed"} | ${feature.command || "command"}`)}</em>
            <small>${escapeHtml(feature.description || "")}</small>
          </div>
        `).join("")}
      </div>
    </article>
  `;
}

function renderComponentFourLinks(platform) {
  const operatorEndpoints = platform.operator_endpoints || [];
  const deploymentLinks = platform.deployment_links || [];
  const connectivity = platform.connectivity || {};
  if (!operatorEndpoints.length && !deploymentLinks.length) {
    return `<p class="empty">No platform links yet.</p>`;
  }
  return `
    <article class="resource-card">
      <div class="resource-head">
        <strong>Operator links</strong>
        <span>${operatorEndpoints.length}</span>
      </div>
      <div class="resource-list">
        ${operatorEndpoints.map((item) => `
          <a class="resource-link" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noreferrer">
            <span>${escapeHtml(item.name || "Endpoint")}</span>
            <em>${escapeHtml(item.status || "link")}</em>
          </a>
        `).join("")}
      </div>
    </article>
    <article class="resource-card">
      <div class="resource-head">
        <strong>Connectivity</strong>
        <span>Live</span>
      </div>
      <div class="resource-list">
        ${renderConnectivityItem("Grafana", connectivity.grafana)}
        ${renderConnectivityItem("Prometheus", connectivity.prometheus)}
        ${renderSuricataConnectivity(connectivity.suricata)}
      </div>
    </article>
    <article class="resource-card">
      <div class="resource-head">
        <strong>Deploy links</strong>
        <span>${deploymentLinks.length}</span>
      </div>
      <div class="resource-list">
        ${deploymentLinks.map((item) => `
          <a class="resource-link" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noreferrer">
            <span>${escapeHtml(item.name || "Platform")}</span>
            <em>${escapeHtml(`${item.scope || "link"} | ${item.status || "docs"}`)}</em>
          </a>
        `).join("")}
      </div>
    </article>
  `;
}

function formatChartValue(value, suffix = "") {
  if (suffix === "ms") {
    return `${Number(value).toFixed(1)} ms`;
  }
  return `${Number(value).toLocaleString()}${suffix ? ` ${suffix}` : ""}`;
}

function renderComponentFourAttackBanner(attackView) {
  const title = attackView.title || "Security monitoring";
  const reason = attackView.reason || "No active incident.";
  const subject = attackView.subject || "No subject";
  const action = attackView.action ? prettify(attackView.action) : "Monitoring";
  const temporaryBlocks = Number(attackView.temporary_blocks || 0);
  const expiry = attackView.expires_at ? `Until ${formatTime(attackView.expires_at)}` : "Watching live traffic";
  return `
    <div class="attack-banner-copy">
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(reason)}</p>
    </div>
    <div class="attack-banner-meta">
      <span>${escapeHtml(subject)}</span>
      <b>${escapeHtml(action)}</b>
      <em>${escapeHtml(expiry)} | ${temporaryBlocks} temp blocks</em>
    </div>
  `;
}

function renderComponentFourIncidentList(incidents) {
  if (!incidents.length) {
    return `<p class="empty">No incidents yet.</p>`;
  }
  return incidents.map((incident) => `
    <article class="incident-item ${escapeHtml(String(incident.status || "observed"))}">
      <div>
        <strong>${escapeHtml(prettify(incident.label || incident.kind || "incident"))}</strong>
        <span>${escapeHtml(incident.subject || "system")}</span>
      </div>
      <div class="incident-meta">
        <em>${escapeHtml(prettify(incident.status || "observed"))}</em>
        ${incident.expires_at ? `<small>Until ${escapeHtml(formatTime(incident.expires_at))}</small>` : ""}
        <small>${escapeHtml(incident.reason || "")}</small>
      </div>
    </article>
  `).join("");
}

function renderComponentFourSubjectList(subjects, allSubjects = []) {
  if (!subjects.length) {
    return `<p class="empty">No hosts available.</p>`;
  }
  const authenticated = Boolean(state.auth?.authenticated);
  return subjects.map((subject) => `
    <article class="subject-row">
      <div class="subject-main">
        <div>
          <strong>${escapeHtml(subject.label || subject.ip || "Subject")}</strong>
          <span>${escapeHtml(subject.ip || "")} | ${escapeHtml(subject.zone || "external")}</span>
        </div>
        <span class="health-pill ${escapeHtml(mapSubjectStatusClass(subject.status))}">${escapeHtml(prettify(subject.status || "observed"))}</span>
      </div>
      <div class="subject-meta">
        <span>Override: ${escapeHtml(prettify(subject.override || "none"))}</span>
        ${subject.expires_at ? `<span>Until ${escapeHtml(formatTime(subject.expires_at))}</span>` : ""}
        ${subject.anomaly_score !== undefined ? `<span>Risk ${escapeHtml(String(subject.anomaly_score))}</span>` : ""}
        ${subject.allowed_targets?.length ? `<span>Allow to ${escapeHtml(subject.allowed_targets.join(", "))}</span>` : ""}
      </div>
      <label class="subject-target-picker">
        <span>Allowed servers</span>
        <select multiple size="4" data-c4-targets-for="${escapeHtml(subject.ip || "")}" ${authenticated ? "" : "disabled"}>
          ${allSubjects
            .filter((candidate) => candidate.ip && candidate.ip !== subject.ip)
            .map((candidate) => `
              <option value="${escapeHtml(candidate.ip)}" ${subject.allowed_targets?.includes(candidate.ip) ? "selected" : ""}>
                ${escapeHtml(candidate.label || candidate.ip)} (${escapeHtml(candidate.ip)})
              </option>
            `).join("")}
        </select>
      </label>
      <div class="subject-actions">
        <button class="mini-button" type="button" data-c4-subject="${escapeHtml(subject.ip || "")}" data-c4-action="allow" ${authenticated ? "" : "disabled"}>Allow Selected</button>
        <button class="mini-button danger" type="button" data-c4-subject="${escapeHtml(subject.ip || "")}" data-c4-action="block" ${authenticated ? "" : "disabled"}>Deny</button>
        <button class="mini-button warning" type="button" data-c4-subject="${escapeHtml(subject.ip || "")}" data-c4-action="temporary_block" ${authenticated ? "" : "disabled"}>Temp Block</button>
      </div>
    </article>
  `).join("");
}

function renderComponentFourRuleStatus(message) {
  if (!message) {
    return `<p class="empty">No security rule added yet.</p>`;
  }
  return `
    <div class="rule-status-copy">
      <strong>Rule Added</strong>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function renderComponentFourRuleList(rules) {
  const items = (rules || []).slice().reverse().slice(0, 6);
  if (!items.length) {
    return `<p class="empty">Rule activity will appear here.</p>`;
  }
  return items.map((rule) => `
    <article class="rule-item ${escapeHtml(String(rule.action || "observe"))}">
      <div>
        <strong>${escapeHtml(prettify(rule.action || "rule"))}</strong>
        <span>${escapeHtml(rule.subject || rule.name || "subject")}</span>
      </div>
      <div class="incident-meta">
        <em>${escapeHtml(rule.id || "rule")}</em>
        <small>${escapeHtml(rule.description || "")}</small>
      </div>
    </article>
  `).join("");
}

function renderComponentFourServerAnalysis(analyses, backends) {
  if (!analyses.length) {
    return `<p class="empty">No IP security analysis yet.</p>`;
  }
  const backendMap = new Map((backends || []).map((backend) => [backend.ip, backend]));
  return analyses.map((item) => {
    const backend = backendMap.get(item.ip);
    const optimizerStatus = backend ? (backend.optimizer_status || (backend.healthy ? "online" : "offline")) : (item.optimizer_effect || "available");
    const detail = backend?.security_reason || item.reason || "No active enforcement";
    return `
      <article class="server-analysis-card ${escapeHtml(mapSubjectStatusClass(item.security_status))}">
        <div class="subject-main">
          <div>
            <strong>${escapeHtml(item.label || item.ip || "Server")}</strong>
            <span>${escapeHtml(item.ip || "")} | ${escapeHtml(item.zone || "external")}</span>
          </div>
          <span class="health-pill ${escapeHtml(mapRiskClass(item.risk_level))}">${escapeHtml(prettify(item.risk_level || "low"))}</span>
        </div>
        <div class="server-analysis-meta">
          <span>Security: ${escapeHtml(prettify(item.security_status || "observed"))}</span>
          <span>Risk ${escapeHtml(String(item.risk_score || 0))}</span>
          <span>Controller: ${escapeHtml(prettify(item.controller_action || "monitor"))}</span>
          <span>Optimizer: ${escapeHtml(prettify(optimizerStatus))}</span>
          ${item.expires_at ? `<span>Until ${escapeHtml(formatTime(item.expires_at))}</span>` : ""}
        </div>
        <p>${escapeHtml(detail)}</p>
      </article>
    `;
  }).join("");
}

function renderConnectivityItem(label, connection) {
  if (!connection) {
    return `<div class="resource-link static"><span>${escapeHtml(label)}</span><em>unknown</em></div>`;
  }
  const status = connection.reachable ? `reachable | ${connection.status}` : (connection.error || "unreachable");
  return `
    <div class="resource-link static">
      <span>${escapeHtml(label)}</span>
      <em>${escapeHtml(status)}</em>
      <small>${escapeHtml(`${Number(connection.latency_ms || 0).toFixed(1)} ms`)}</small>
    </div>
  `;
}

function renderSuricataConnectivity(connection) {
  if (!connection) {
    return `<div class="resource-link static"><span>Suricata</span><em>unknown</em></div>`;
  }
  return `
    <div class="resource-link static">
      <span>Suricata</span>
      <em>${escapeHtml(`${connection.installed ? "installed" : "not installed"} | ${connection.running ? "running" : "not running"}`)}</em>
      <small>${escapeHtml(connection.command || "binary not found")}</small>
    </div>
  `;
}

function mapSubjectStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("allow") || value === "active" || value === "observed") {
    return "healthy";
  }
  if (value.includes("temp") || value.includes("suspicious")) {
    return "warning";
  }
  return "offline";
}

function mapRiskClass(level) {
  const value = String(level || "").toLowerCase();
  if (value === "low") {
    return "healthy";
  }
  if (value === "medium") {
    return "warning";
  }
  return "offline";
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
