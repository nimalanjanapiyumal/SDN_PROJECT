# Architecture Overview

The completed development package follows a controller-centered integration pattern.

- **Northbound inputs**: intents, context, optimizer plans, ML recommendations, and security actions.
- **Decision layer**: priority arbitration using the integrated policy engine.
- **Execution layer**: a Linux-safe execution adapter that records applied actions and can be extended to push actions to Ryu or another SDN southbound service.
- **Observability layer**: Prometheus exporter metrics and provisioned Grafana dashboard.

## Main runtime services

- `adaptive_cloud_platform.app` - primary FastAPI application
- `adaptive_cloud_platform.services.orchestrator_service` - state and policy coordination
- `adaptive_cloud_platform.services.resource_optimizer_service` - RR + GA backend optimizer wrapper
- `adaptive_cloud_platform.services.ml_service` - rule-based fallback and model-friendly recommendation service
- `adaptive_cloud_platform.services.security_service` - compatibility wrappers for authentication, segmentation, and CTI events
