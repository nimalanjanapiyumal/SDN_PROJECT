# Evaluation Plan

## Main Scenarios

1. Normal traffic
2. High traffic load
3. Congestion
4. Malicious source IP
5. Suspicious user behavior
6. Lateral movement attempt
7. Conflicting policies
8. Controller scalability

## Metrics

- latency
- throughput
- packet loss
- CPU usage
- memory usage
- bandwidth usage
- active flows
- flow installation count
- controller response time
- threat alert count
- SLA violation count
- prediction accuracy
- mitigation latency
- controller overhead

## Validation Goals

- verify host discovery
- verify intent submission and translation
- verify flow install / delete behavior
- verify RR + GA load balancing decisions
- verify ML prediction pipeline
- verify micro-segmentation and quarantine
- verify CTI / Suricata alert blocking
- verify GUI, Mininet, and controller sync
- verify Prometheus / Grafana runtime visibility

## Recommended Development Order

1. Mininet topology
2. Basic Ryu controller
3. Host discovery
4. REST APIs
5. Intent submission
6. Flow installation
7. Load balancing
8. Monitoring
9. Grafana dashboards
10. ML prediction
11. Security blocking
12. Micro-segmentation
13. Continuous authentication
14. Threat intelligence integration
15. Conflict resolution
16. End-to-end evaluation
