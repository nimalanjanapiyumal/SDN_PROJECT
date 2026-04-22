# Evaluation Plan

This guide turns the bundle into a repeatable experiment for your research objectives.

## Goal

Compare a static SDN monitoring setup against the adaptive ML-driven loop.

## Experiment modes

### Baseline mode
Run:

- Prometheus
- Grafana
- controller
- topology

Do **not** run the policy agent.

### Adaptive mode
Run all of the above **plus** the ML policy agent.

## Scenarios

Use the same topology and repeat these scenarios in both modes:

1. `normal`
2. `congestion`
3. `ddos`
4. `port_scan`

## Metrics to capture

### 1. Prediction accuracy
Use the known scenario label as the ground truth and compare it to the model output exposed by:

- `cloud_sdn_prediction_class`
- `cloud_sdn_prediction_score`

### 2. Mitigation latency
Use:

- `cloud_sdn_last_mitigation_latency_ms`

### 3. SLA risk
Use:

- `cloud_sdn_sla_risk_score`

### 4. Resource utilization
Use:

- `cloud_sdn_link_utilization_ratio`
- `cloud_sdn_controller_cpu_percent`
- `cloud_sdn_controller_memory_percent`

### 5. Traffic intensity
Use:

- `cloud_sdn_packet_rate_per_sec`
- `cloud_sdn_byte_rate_per_sec`
- `cloud_sdn_packet_in_rate_per_sec`

## Example PromQL queries

### Aggregate traffic rate
```promql
sum(cloud_sdn_packet_rate_per_sec)
sum(cloud_sdn_byte_rate_per_sec)
```

### Maximum link utilization
```promql
max(cloud_sdn_link_utilization_ratio)
```

### Latest SLA risk
```promql
cloud_sdn_sla_risk_score
```

### Number of mitigations
```promql
sum by(action) (cloud_sdn_mitigations_total)
sum by(action) (cloud_sdn_policy_actions_total)
```

## Suggested procedure

### Baseline
1. `bash scripts/start_observability.sh`
2. `bash scripts/start_controller.sh`
3. `bash scripts/run_topology.sh --foreground --scenario congestion`
4. record dashboard values or Prometheus snapshots
5. repeat for `ddos` and `port_scan`

### Adaptive
1. `bash scripts/start_observability.sh`
2. `bash scripts/start_controller.sh`
3. `bash scripts/start_policy_agent.sh`
4. `bash scripts/run_topology.sh --foreground --scenario congestion`
5. record changes in utilization and mitigation latency
6. repeat for `ddos` and `port_scan`

## Expected observations

### With adaptive mode enabled
- lower persistence of abnormal traffic,
- lower sustained peak utilization during congestion,
- faster control response,
- more stable SLA-risk trends after mitigation.

## Thesis-friendly reporting table

| Scenario | Mode | Peak Utilization | Avg Packet Rate | Mitigation Latency | SLA Risk | Observation |
|---|---|---:|---:|---:|---:|---|
| Congestion | Baseline |  |  | N/A |  |  |
| Congestion | Adaptive |  |  |  |  |  |
| DDoS | Baseline |  |  | N/A |  |  |
| DDoS | Adaptive |  |  |  |  |  |
| Port Scan | Baseline |  |  | N/A |  |  |
| Port Scan | Adaptive |  |  |  |  |  |
