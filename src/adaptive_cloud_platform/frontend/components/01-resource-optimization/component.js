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
    "GET /api/v1/backends",
    "POST /api/v1/resource-plans",
    "POST /api/v1/resource-plans/recompute"
  ],
  capabilities: [
    "Backend health and weight visibility",
    "RR per-flow selection",
    "GA recomputation for longer-term optimization",
    "VIP and backend capacity mapping"
  ],
  signals: ["backend_weights", "active_connections", "latency_ms", "throughput_mbps"]
};
