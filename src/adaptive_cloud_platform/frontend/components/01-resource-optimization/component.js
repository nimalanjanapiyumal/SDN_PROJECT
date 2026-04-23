export const resourceOptimization = {
  id: "component-1",
  number: "01",
  title: "Resource Optimization",
  shortTitle: "Optimizer",
  subtitle: "Hybrid Round Robin and Genetic Algorithm load balancing",
  owner: "Component 1",
  accent: "green",
  sourceFolders: [
    "src/sdn_hybrid_lb/",
    "src/adaptive_cloud_platform/services/resource_optimizer_service.py",
    "sources/SDN_CLOUD_1-master/"
  ],
  routes: [
    "GET /api/v1/component-1/status",
    "POST /api/v1/component-1/route",
    "POST /api/v1/component-1/backends/{name}/metrics",
    "POST /api/v1/component-1/backends/{name}/health",
    "POST /api/v1/component-1/workload/simulate",
    "GET /api/v1/backends",
    "POST /api/v1/resource-plans",
    "POST /api/v1/resource-plans/recompute"
  ],
  capabilities: [
    "Real-time RR/SWRR routing and SDN flow-rule generation",
    "GA recomputation for longer-term CPU, memory, bandwidth, and connection optimization",
    "RR-vs-GA conflict resolution through health and overload gates",
    "Fault tolerance through backend exclusion and fast redistribution",
    "SLA compliance tracking for latency-sensitive cloud requests"
  ],
  signals: ["backend_weights", "active_connections", "latency_ms", "throughput_mbps", "sla_compliance"]
};
