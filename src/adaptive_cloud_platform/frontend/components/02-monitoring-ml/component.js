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
    "POST /api/v1/context",
    "GET /api/v1/state",
    "GET /metrics"
  ],
  capabilities: [
    "Network context submission",
    "Latency and packet-rate tracking",
    "Anomaly and congestion recommendation",
    "Prometheus exporter compatibility"
  ],
  signals: ["latency_ms", "packet_in_rate_per_sec", "max_link_utilization_ratio", "recommendation"]
};
