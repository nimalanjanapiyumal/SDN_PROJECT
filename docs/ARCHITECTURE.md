# SDN Adaptive Cloud Framework Architecture

## Goal

Build one controller-centered SDN platform that can monitor the cloud fabric, translate intents, optimize resource usage, predict risk, enforce security, and expose everything through clean REST APIs.

## High-Level Architecture

1. `User / Admin`
2. `Intent Submission API`
3. `Intelligent SDN Controller`
4. `Resource Optimization Module`
5. `Security Enforcement Module`
6. `Monitoring and ML Module`
7. `SDN Data Plane`

## Main Runtime Modules

- `src/adaptive_cloud_platform/app.py`
  - FastAPI integration layer
  - compatibility APIs and component APIs
- `src/adaptive_cloud_platform/services/intent_controller_service.py`
  - intent parsing
  - DFPS-style priority scoring
  - OpenFlow-compatible rule generation
  - host inventory
- `src/adaptive_cloud_platform/services/resource_optimizer_service.py`
  - Round Robin
  - weighted routing
  - GA-backed optimization
- `src/adaptive_cloud_platform/services/monitoring_ml_service.py`
  - telemetry normalization
  - ML prediction
  - policy feedback loop
- `src/adaptive_cloud_platform/services/security_service.py`
  - continuous authentication
  - micro-segmentation
  - CTI / Suricata-style response
- `src/adaptive_cloud_platform/services/sdn_runtime_service.py`
  - Mininet / Ryu / Prometheus / Grafana / OpenStack runtime visibility
  - topology and controller state sync
- `src/adaptive_cloud_platform/sdn/ryu_integrated_app.py`
  - OpenFlow controller bridge
  - runtime event sync back to GUI/API
- `src/topology/adaptive_cloud_topology.py`
  - Mininet topology and attack scenarios

## Clean Module Mapping to Development Outline

- `Module 1: Intelligent SDN Controller`
  - `app.py`
  - `intent_controller_service.py`
  - `ryu_integrated_app.py`
- `Module 2: Intent Processing Engine`
  - `intent_controller_service.py`
- `Module 3: Dynamic Flow Priority Scheduling`
  - `intent_controller_service.py`
  - orchestration logic in `app.py`
- `Module 4: Hybrid Load Balancing and Resource Optimization`
  - `resource_optimizer_service.py`
- `Module 5: Monitoring and Visualization`
  - `monitoring_ml_service.py`
  - `monitoring/`
  - frontend dashboard
- `Module 6: ML-Based Prediction`
  - `monitoring_ml_service.py`
  - `ml/`
- `Module 7: Adaptive Security Enforcement`
  - `security_service.py`

## Runtime Data Flow

1. Admin submits intent or policy request.
2. Monitoring publishes live context.
3. ML predicts congestion, anomaly, or SLA risk.
4. Security publishes alerts or risk signals.
5. Controller ranks actions.
6. Flow rules are generated.
7. Ryu / GUI runtime state is updated.
8. Prometheus and Grafana expose the state visually.
