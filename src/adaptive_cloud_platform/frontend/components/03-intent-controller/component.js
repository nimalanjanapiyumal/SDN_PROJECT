export const intentController = {
  id: "component-3",
  number: "03",
  title: "Intent Controller",
  shortTitle: "Controller",
  subtitle: "Context-aware intent processing, DFPS scoring, and OpenFlow-compatible rule generation",
  owner: "Component 3",
  accent: "indigo",
  sourceFolders: [
    "src/adaptive_cloud_platform/services/orchestrator_service.py",
    "src/adaptive_cloud_platform/services/intent_controller_service.py",
    "src/topology/",
    "sources/SDN-main/",
    "sources/SDN_CLOUD_2-master/controller/"
  ],
  routes: [
    "GET /api/v1/component-3/status",
    "POST /api/v1/component-3/intents",
    "POST /api/v1/component-3/context",
    "GET /api/v1/component-3/rules",
    "GET /api/v1/component-3/hosts",
    "POST /api/v1/component-3/benchmark",
    "POST /api/v1/intents",
    "POST /api/intent/submit",
    "GET /api/network/hosts"
  ],
  capabilities: [
    "Natural-language intent classification",
    "DFPS-aligned dynamic priority scoring",
    "Multi-dimensional context adaptation",
    "OpenFlow-compatible rule generation",
    "Host discovery and team API compatibility"
  ],
  signals: ["intent", "priority", "threat", "congestion", "load", "context_score"]
};
