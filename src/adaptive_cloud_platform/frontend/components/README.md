# Frontend Component Structure

The frontend mirrors the four delivery components so UI copy, routes, and folders stay traceable:

- `01-resource-optimization/` maps to the hybrid RR + GA load-balancing component.
- `02-monitoring-ml/` maps to monitoring, visualization, telemetry, and ML recommendations.
- `03-intent-controller/` maps to the context-aware SDN controller and intent APIs.
- `04-security-enforcement/` maps to continuous authentication, micro-segmentation, and CTI actions.

Shared browser behavior lives in `../assets/js/app.js`, and shared styling lives in `../assets/css/styles.css`.
