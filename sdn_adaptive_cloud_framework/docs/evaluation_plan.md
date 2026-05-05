# Evaluation plan

## Metrics (outline section 13)

* Latency
* Throughput
* Packet loss
* CPU usage
* Memory usage
* SLA compliance rate
* Prediction accuracy / F1
* Mitigation latency (alert -> drop rule installed)
* Controller overhead under load

## Scenarios

| # | Scenario | Goal | Driver |
| - | -------- | ---- | ------ |
| 1 | Normal traffic | Verify forwarding + monitoring | iperf3 over Mininet |
| 2 | High traffic load | Hybrid LB activation | hping3 / iperf3 parallel |
| 3 | Congestion | ML prediction + reroute | inject latency via tc |
| 4 | Malicious source IP | CTI block intent | `scenario_block_malicious_ip` |
| 5 | Suspicious user | Continuous-auth quarantine | `score_session` -> intent |
| 6 | Lateral movement | Micro-segmentation | `scenario_lateral_movement_block` |
| 7 | Conflicting policies | DFPS ordering | `scenario_conflicting_intents` |
| 8 | Controller scalability | Throughput under host load | wrk against `/api/intent/submit` |

## Procedure

1. Start the controller: `uvicorn sdn_adaptive_cloud_framework.api.app:app --host 0.0.0.0 --port 8080`.
2. Start Ryu: `ryu-manager --observe-links sdn_adaptive_cloud_framework.controller.ryu_controller`.
3. Start Mininet topology: `sudo python3 -m sdn_adaptive_cloud_framework.topology.mininet_topology`.
4. Start Prometheus + Grafana via the existing `docker-compose.yml`.
5. Run the scripted scenario(s) and capture metrics from Prometheus / Grafana.

## Expected outcomes

* Scenario 4: drop rule is installed within < 1 s of the malicious IP being announced.
* Scenario 7: when both a load-balancing and a security intent target the same flow, the security intent wins (verified by `tests/test_controller.py::test_dfps_security_beats_load_balancing_under_threat`).
* Scenario 8: controller overhead grows sub-linearly with concurrent intent submissions thanks to the in-memory state and lock-per-section design.
