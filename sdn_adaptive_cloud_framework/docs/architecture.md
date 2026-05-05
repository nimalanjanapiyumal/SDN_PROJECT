# Architecture

## Overview

The framework follows the high-level architecture in section 2 of the development outline. The Intelligent SDN Controller is the integration point: it receives user intents, monitoring context, ML predictions and security alerts, and produces OpenFlow flow rules.

```
User / Admin
    |
    v
REST API (api/)
    |
    v
Controller State (controller/controller_state.py)
    |
    +------ Intent Processor (Module 2)
    +------ DFPS Engine (Module 3)
    +------ Host Registry
    +------ Topology Manager
    +------ Flow Manager  ----> Ryu OFPFlowMod ----> OpenFlow switches
    |
    +<----- Resource Optimizer (load_balancer/, Module 4)
    +<----- ML Predictor (ml_module/, Module 6)
    +<----- Security Engine (security/, Module 7)
    +<----- Monitoring  (monitoring/, Module 5)
```

## Shared state

`controller/controller_state.py` defines a singleton `ControllerState`. Both the FastAPI app (`api/app.py`) and the Ryu app (`controller/ryu_controller.py`) call `get_state()` so a flow learned by Ryu and an intent submitted via REST end up in the same data structures.

When Ryu is not running (CI, local laptop, unit tests), the `FlowManager` records intents in memory only; when Ryu *is* running, the same install path additionally builds an `OFPFlowMod` and sends it to the registered datapath.

## Intent pipeline

1. POST `/api/intent/submit` -> Pydantic schema -> `validate_intent`
2. The validated `Intent` is stored, then ranked against all current intents using `rank_intents(intents, current_context)`.
3. The intent's final priority is overwritten with the DFPS result.
4. `translate_intent` returns an OpenFlow-compatible `match`/`flow_action` dict.
5. `FlowManager.install` records the flow and (if connected) pushes it to every known datapath.

## DFPS priority order

When multiple intents conflict, ordering follows section 3 of the outline:

1. Security enforcement
2. SLA / segmentation
3. Congestion avoidance / monitoring
4. Load balancing
5. General optimization

Context-driven boosts: high threat -> +50 to security intents; high congestion -> +30 to load-balancing; latency > 100 ms -> +20 to optimization intents; high SLA risk -> +25 to optimization/load-balancing.

## Module boundaries

| Module | Folder | External interface |
| ------ | ------ | ------------------ |
| 1 SDN controller | `controller/` | Python imports + Ryu events |
| 2 Intent processor | `controller/intent_processor.py` | `validate_intent`, `translate_intent` |
| 3 DFPS engine | `controller/dfps_engine.py` | `rank_intents`, `detect_conflicts` |
| 4 Load balancer | `load_balancer/` | `HybridLoadBalancer.select` |
| 5 Monitoring | `monitoring/` | Prometheus exporter on `:9108/metrics` |
| 6 ML predictor | `ml_module/` | FastAPI app on its own port |
| 7 Security | `security/` | Plain functions returning intent dicts |
