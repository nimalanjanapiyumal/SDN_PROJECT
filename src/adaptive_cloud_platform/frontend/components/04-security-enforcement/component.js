export const securityEnforcement = {
  id: "component-4",
  number: "04",
  title: "Security Enforcement",
  shortTitle: "Security",
  subtitle: "Continuous authentication, micro-segmentation, and CTI mitigation",
  owner: "Component 4",
  accent: "coral",
  sourceFolders: [
    "src/security_modules/",
    "src/adaptive_cloud_platform/services/security_service.py",
    "sources/SDN-Security--main/"
  ],
  routes: [
    "GET /api/v1/component-4/status",
    "POST /api/v1/component-4/auth/login",
    "POST /api/v1/component-4/auth/verify",
    "POST /api/v1/component-4/segmentation/enforce",
    "POST /api/v1/component-4/segmentation/evaluate",
    "POST /api/v1/component-4/cti/fetch",
    "POST /api/v1/component-4/cti/alert",
    "GET /api/v1/component-4/rules",
    "POST /api/v1/security-actions",
    "POST /api/v1/policy/enforce",
    "POST /sdn/block",
    "POST /sdn/quarantine",
    "POST /sdn/release"
  ],
  capabilities: [
    "Continuous authentication anomaly scoring",
    "Zero Trust micro-segmentation ACLs",
    "Dynamic CTI and Suricata-style blocking",
    "Block, quarantine, release, and allow actions",
    "Security-first priority in the decision spine",
    "OpenFlow-compatible security rule records"
  ],
  signals: ["anomaly_score", "src_ip", "dst_ip", "ioc", "severity", "mitigation_latency_ms"]
};
