import { componentConfigs } from "../../components/index.js";

const state = {
  selectedComponentId: componentConfigs[0].id,
  snapshot: null,
  health: null,
  backends: [],
  autoRefresh: true,
  timer: null
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  renderComponentNav();
  renderComponentPanel();
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
    "recomputeBtn",
    "componentNav",
    "componentPanel",
    "decisionCount",
    "policyCount",
    "hostCount",
    "backendCount",
    "latestDecisionTitle",
    "latestDecisionSource",
    "latestDecisionScore",
    "latestDecisionMode",
    "latestDecisionJson",
    "backendList",
    "eventTimeline",
    "apiMatrix",
    "toast",
    "intentForm",
    "contextForm",
    "securityForm"
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
  els.apiBase.textContent = window.location.origin;
}

function bindEvents() {
  els.refreshBtn.addEventListener("click", () => refreshAll());
  els.autoRefresh.addEventListener("change", (event) => {
    state.autoRefresh = event.target.checked;
  });
  els.recomputeBtn.addEventListener("click", recomputePlan);

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => activateTab(tab.dataset.tab));
  });

  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.addEventListener("click", () => fillScenario(button.dataset.scenario));
  });

  els.intentForm.addEventListener("submit", submitIntent);
  els.contextForm.addEventListener("submit", submitContext);
  els.securityForm.addEventListener("submit", submitSecurity);
}

async function refreshAll(options = {}) {
  setApiStatus("loading", "Refreshing");
  try {
    const [health, snapshot, backendResponse] = await Promise.all([
      apiRequest("/healthz"),
      apiRequest("/api/v1/state"),
      apiRequest("/api/v1/backends")
    ]);
    state.health = health;
    state.snapshot = snapshot;
    state.backends = backendResponse.backends || [];
    renderState();
    setApiStatus("online", "Online");
    if (!options.quiet) {
      showToast("State refreshed");
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
    throw new Error(`${response.status} ${response.statusText}: ${body.slice(0, 120)}`);
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function renderState() {
  const snapshot = state.snapshot || {};
  const decisions = snapshot.decisions || [];
  const activePolicies = snapshot.active_policies || {};
  const hosts = snapshot.hosts || {};
  const latestDecision = decisions[decisions.length - 1];

  els.decisionCount.textContent = decisions.length;
  els.policyCount.textContent = Object.keys(activePolicies).length;
  els.hostCount.textContent = Object.keys(hosts).length;
  els.backendCount.textContent = state.backends.length;

  if (latestDecision) {
    els.latestDecisionTitle.textContent = prettify(latestDecision.decision_type);
    els.latestDecisionSource.textContent = latestDecision.source || "unknown";
    els.latestDecisionScore.textContent = latestDecision.score ?? 0;
    els.latestDecisionMode.textContent = latestDecision.execution?.mode || "record";
    els.latestDecisionJson.textContent = JSON.stringify(latestDecision.payload || {}, null, 2);
  } else {
    els.latestDecisionTitle.textContent = "Observe";
    els.latestDecisionSource.textContent = "none";
    els.latestDecisionScore.textContent = "0";
    els.latestDecisionMode.textContent = "record";
    els.latestDecisionJson.textContent = "{}";
  }

  renderBackends();
  renderTimeline();
  renderComponentPanel();
  renderComponentNav();
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
    });
  });
}

function renderComponentPanel() {
  const component = getSelectedComponent();
  const snapshot = state.snapshot || {};
  const latestByComponent = {
    "component-1": lastItem(snapshot.resource_plans),
    "component-2": lastItem(snapshot.contexts),
    "component-3": lastItem(snapshot.intents),
    "component-4": lastItem(snapshot.security_actions)
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
    <div class="component-columns">
      <div>
        <h3>Capabilities</h3>
        <ul class="clean-list">
          ${component.capabilities.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
        </ul>
      </div>
      <div>
        <h3>Signals</h3>
        <div class="chips">
          ${component.signals.map((item) => `<code>${escapeHtml(item)}</code>`).join("")}
        </div>
      </div>
    </div>
    <div class="component-columns">
      <div>
        <h3>Related Folders</h3>
        <ul class="path-list">
          ${component.sourceFolders.map((item) => `<li><code>${escapeHtml(item)}</code></li>`).join("")}
        </ul>
      </div>
      <div>
        <h3>Latest Payload</h3>
        <pre>${escapeHtml(JSON.stringify(latest, null, 2))}</pre>
      </div>
    </div>
  `;
}

function renderBackends() {
  if (!state.backends.length) {
    els.backendList.innerHTML = `<p class="empty">No backend data yet.</p>`;
    return;
  }
  const maxWeight = Math.max(...state.backends.map((backend) => Number(backend.weight || 0)), 1);
  els.backendList.innerHTML = state.backends.map((backend) => {
    const weight = Number(backend.weight || 0);
    const width = Math.max(6, Math.round((weight / maxWeight) * 100));
    const metrics = backend.metrics || {};
    const capacity = backend.capacity || {};
    return `
      <article class="backend-row">
        <div class="backend-main">
          <strong>${escapeHtml(backend.name)}</strong>
          <span>${escapeHtml(backend.ip)} | dpid ${backend.dpid} port ${backend.port}</span>
        </div>
        <div class="weight-bar" aria-label="Weight ${weight.toFixed(2)}">
          <span style="width: ${width}%"></span>
        </div>
        <div class="backend-meta">
          <span>${backend.healthy ? "healthy" : "offline"}</span>
          <span>w ${weight.toFixed(2)}</span>
          <span>${capacity.cpu_cores || 0} CPU</span>
          <span>${metrics.active_connections || 0} flows</span>
        </div>
      </article>
    `;
  }).join("");
}

function renderTimeline() {
  const snapshot = state.snapshot || {};
  const events = [
    ...(snapshot.security_actions || []).map((item) => ({ kind: "security", label: item.action, item })),
    ...(snapshot.intents || []).map((item) => ({ kind: "intent", label: item.type, item })),
    ...(snapshot.contexts || []).map((item) => ({ kind: "context", label: item.recommendation || item.source, item })),
    ...(snapshot.resource_plans || []).map((item) => ({ kind: "plan", label: "resource plan", item })),
    ...(snapshot.decisions || []).map((item) => ({ kind: "decision", label: item.decision_type, item }))
  ].sort((a, b) => Number(b.item.executed_at || b.item.ts || 0) - Number(a.item.executed_at || a.item.ts || 0)).slice(0, 10);

  if (!events.length) {
    els.eventTimeline.innerHTML = `<p class="empty">No events yet.</p>`;
    return;
  }

  els.eventTimeline.innerHTML = events.map((event) => {
    const ts = event.item.executed_at || event.item.ts;
    return `
      <article class="timeline-item">
        <span class="timeline-kind">${escapeHtml(event.kind)}</span>
        <strong>${escapeHtml(prettify(event.label || "event"))}</strong>
        <time>${formatTime(ts)}</time>
      </article>
    `;
  }).join("");
}

function renderApiMatrix() {
  els.apiMatrix.innerHTML = componentConfigs.map((component) => `
    <article class="matrix-card ${component.accent}">
      <div>
        <span>${component.number}</span>
        <h3>${escapeHtml(component.title)}</h3>
      </div>
      <ul>
        ${component.routes.map((route) => `<li><code>${escapeHtml(route)}</code></li>`).join("")}
      </ul>
    </article>
  `).join("");
}

async function recomputePlan() {
  try {
    const result = await apiRequest("/api/v1/resource-plans/recompute", { method: "POST", body: "{}" });
    showToast(`Plan recomputed: ${prettify(result.decision?.decision_type || "optimizer")}`);
    await refreshAll({ quiet: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function submitIntent(event) {
  event.preventDefault();
  const payload = {
    type: valueOf("intentType"),
    intent: valueOf("intentText"),
    priority: Number(valueOf("intentPriority")),
    src_ip: valueOf("intentSrc"),
    dst_ip: valueOf("intentDst"),
    metadata: {
      submitted_from: "frontend"
    }
  };
  await submitJson("/api/v1/intents", payload, "Intent submitted");
}

async function submitContext(event) {
  event.preventDefault();
  const payload = {
    source: "frontend-monitoring",
    max_link_utilization_ratio: Number(valueOf("linkUtil")) / 100,
    latency_ms: Number(valueOf("latencyMs")),
    packet_in_rate_per_sec: Number(valueOf("packetRate")),
    controller_cpu_percent: Number(valueOf("controllerCpu"))
  };
  await submitJson("/api/v1/context", payload, "Context published");
}

async function submitSecurity(event) {
  event.preventDefault();
  const payload = {
    source: "frontend-security",
    action: valueOf("securityAction"),
    subject: valueOf("securitySubject"),
    severity: Number(valueOf("securitySeverity")),
    reason: valueOf("securityReason")
  };
  await submitJson("/api/v1/security-actions", payload, "Security action enforced");
}

async function submitJson(path, payload, message) {
  try {
    await apiRequest(path, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(message);
    await refreshAll({ quiet: true });
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

function fillScenario(name) {
  const scenarios = {
    normal: { linkUtil: 34, latencyMs: 48, packetRate: 90, controllerCpu: 35 },
    congestion: { linkUtil: 84, latencyMs: 190, packetRate: 330, controllerCpu: 71 },
    ddos: { linkUtil: 96, latencyMs: 260, packetRate: 850, controllerCpu: 88 }
  };
  const scenario = scenarios[name];
  Object.entries(scenario).forEach(([id, value]) => {
    document.getElementById(id).value = value;
  });
}

function getComponentCounts() {
  const snapshot = state.snapshot || {};
  return {
    "component-1": (snapshot.resource_plans || []).length,
    "component-2": (snapshot.contexts || []).length,
    "component-3": (snapshot.intents || []).length,
    "component-4": (snapshot.security_actions || []).length
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

function valueOf(id) {
  return document.getElementById(id).value.trim();
}

function lastItem(items = []) {
  return items.length ? items[items.length - 1] : null;
}

function prettify(value = "") {
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
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
