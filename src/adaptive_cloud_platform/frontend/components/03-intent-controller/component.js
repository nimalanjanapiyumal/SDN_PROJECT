export const intentController = {
  id: "component-3",
  number: "03",
  title: "Intent Controller",
  shortTitle: "Controller",
  subtitle: "Context-aware intent processing and SDN controller compatibility",
  owner: "Component 3",
  accent: "indigo",
  sourceFolders: [
    "src/adaptive_cloud_platform/services/orchestrator_service.py",
    "src/topology/",
    "sources/SDN-main/",
    "sources/SDN_CLOUD_2-master/controller/"
  ],
  routes: [
    "POST /api/v1/intents",
    "POST /api/intent/submit",
    "GET /api/network/hosts"
  ],
  capabilities: [
    "Intent submission and priority arbitration",
    "DFPS-aligned dynamic decision ordering",
    "Host discovery API compatibility",
    "Execution adapter for SDN flow-rule integration"
  ],
  signals: ["type", "priority", "src_ip", "dst_ip"]
};
