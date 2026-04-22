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
    "POST /api/v1/security-actions",
    "POST /api/v1/policy/enforce",
    "POST /sdn/block",
    "POST /sdn/quarantine",
    "POST /sdn/release"
  ],
  capabilities: [
    "Block, quarantine, release, and allow actions",
    "Security-first priority in the decision spine",
    "CTI subject tracking",
    "Zero Trust segmentation workflow hooks"
  ],
  signals: ["action", "subject", "severity", "reason"]
};
