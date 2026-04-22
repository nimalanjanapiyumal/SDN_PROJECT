# System Architecture

## Overview

The framework is composed of five tightly coupled layers:

1. **Emulation layer** - Mininet builds a cloud-like SDN topology with redundant paths.
2. **Control layer** - Ryu enforces forwarding, topology awareness, and adaptive policies.
3. **Monitoring layer** - Prometheus scrapes controller and ML-agent metrics.
4. **Visualization layer** - Grafana presents operational state and ML-driven risk insights.
5. **Intelligence layer** - the policy agent classifies traffic conditions and posts mitigations.

## Main components

### 1. Mininet topology
The topology creates:

- client hosts: `h1`, `h2`
- attack/scanner host: `h3`
- service host: `h4`
- edge switch: `s1`
- two alternate core switches: `s2`, `s3`
- service-edge switch: `s4`

This allows at least two viable paths from the client segment to the service segment:

- primary: `s1 -> s2 -> s4`
- alternate: `s1 -> s3 -> s4`

### 2. Adaptive Ryu controller
The controller performs:

- L2/L3-aware forwarding for new flows
- topology discovery with `--observe-links`
- flow and port statistics collection
- Prometheus metric export
- REST-based policy enforcement
- mitigation lifecycle management

### 3. Prometheus
Prometheus scrapes:

- `http://127.0.0.1:9101/metrics` from the controller
- `http://127.0.0.1:9102/metrics` from the ML policy agent

### 4. Grafana
The dashboard visualizes:

- active flows
- packet and byte rates
- controller CPU and memory
- packet-in rate
- maximum link utilization
- SLA-risk score
- predicted traffic state
- mitigation counters

### 5. ML policy agent
The policy agent:

- queries Prometheus for the latest telemetry
- builds a feature vector
- runs two models:
  - a classifier for network state
  - a regressor for SLA-risk estimation
- identifies the top talker from controller state
- pushes `block` or `reroute` actions to the controller

## Decision loop

```text
Mininet traffic
   ↓
Ryu flow + port stats
   ↓
Prometheus scraping
   ↓
ML inference
   ↓
Controller policy API
   ↓
Adaptive flow updates
```

## Controller API

### `GET /api/v1/state`
Returns:

- aggregated metrics
- known hosts
- current mitigations
- top talkers
- current topology paths

### `GET /api/v1/mitigations`
Returns only mitigation records.

### `POST /api/v1/policy/enforce`
Supported actions:

- `block`
- `reroute`
- `clear`

## Metrics exposed by the controller

- `cloud_sdn_active_flows`
- `cloud_sdn_total_packets`
- `cloud_sdn_total_bytes`
- `cloud_sdn_packet_rate_per_sec`
- `cloud_sdn_byte_rate_per_sec`
- `cloud_sdn_packet_in_rate_per_sec`
- `cloud_sdn_link_utilization_ratio`
- `cloud_sdn_controller_cpu_percent`
- `cloud_sdn_controller_memory_percent`
- `cloud_sdn_last_mitigation_latency_ms`
- `cloud_sdn_mitigations_total`

## Metrics exposed by the ML agent

- `cloud_sdn_prediction_score`
- `cloud_sdn_sla_risk_score`
- `cloud_sdn_prediction_class{label=...}`
- `cloud_sdn_policy_actions_total{action=...}`

## Security enforcement model

When the classifier predicts `ddos` or `port_scan` with sufficiently high confidence:

1. the agent identifies a suspicious source IP,
2. it posts a `block` policy,
3. the controller installs high-priority drop rules,
4. the mitigation expires automatically after the configured duration.

## Resource optimization model

When the classifier predicts `congestion`:

1. the agent identifies the top high-volume flow,
2. it posts a `reroute` policy,
3. the controller chooses the alternate path,
4. broad IP-based flow rules with higher priority override the default path.

## Failure handling

The design includes simple resilience measures:

- if Prometheus is unavailable, the policy agent can derive metrics from controller state;
- if alternate paths are not available, the controller returns a descriptive error rather than silently failing;
- mitigations are automatically expired and cleaned from controller memory.
