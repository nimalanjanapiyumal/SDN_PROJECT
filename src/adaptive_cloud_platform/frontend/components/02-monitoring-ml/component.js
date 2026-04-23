export const monitoringMl = {
  id: "component-2",
  number: "02",
  title: "Monitoring and ML",
  shortTitle: "Monitoring",
  subtitle: "Prometheus, Grafana, telemetry, and ML policy recommendations",
  owner: "Component 2",
  accent: "gold",
  sourceFolders: [
    "src/ml/",
    "src/adaptive_cloud_platform/services/ml_service.py",
    "monitoring/"
  ],
  routes: [
    "GET /api/v1/component-2/status",
    "POST /api/v1/component-2/telemetry",
    "POST /api/v1/component-2/models/train",
    "GET /api/v1/component-2/platform",
    "POST /api/v1/context",
    "GET /api/v1/state",
    "GET /metrics"
  ],
  capabilities: [
    "Network telemetry ingestion and history",
    "Latency, throughput, CPU, memory, flow, and packet-in tracking",
    "ML anomaly, congestion, DDoS, and port-scan prediction",
    "Automatic feedback into Component 1 allocation and orchestration",
    "Prometheus exporter and Grafana dashboard compatibility"
  ],
  signals: ["active_flows", "packet_rate_per_sec", "max_link_utilization_ratio", "label", "sla_risk_score"]
};
