# Project Module Alignment

## Title

**An SDN-Based Adaptive Cloud Network Management Framework with Resource Optimization, Security Enforcement, and ML-Driven Intelligence**

## Research problem

How can monitoring and machine learning be integrated into an SDN-enabled cloud environment to predict anomalies, visualize performance, and enforce adaptive policies in real time?

## Objectives implemented in this bundle

### Main objective
Design and implement an SDN monitoring and optimization framework that integrates real-time visualization with ML-driven predictive intelligence for adaptive cloud network management.

### Specific objectives
- Deploy Prometheus and Grafana for SDN/cloud monitoring.
- Train ML models to detect anomalies, congestion, and security risks.
- Develop a feedback loop between monitoring tools and the Ryu SDN controller.
- Evaluate mitigation latency, utilization, and SLA-risk behavior against a non-adaptive baseline.

## Methodology mapping

### Monitoring layer
Implemented through:
- controller Prometheus exporter on port `9101`
- Prometheus scrape configuration
- alert rules for utilization, prediction risk, and packet-in spikes

### Visualization layer
Implemented through:
- provisioned Grafana datasource
- provisioned dashboard JSON
- panels for flow count, utilization, packet rate, CPU, memory, predicted class, and mitigation counts

### ML module
Implemented through:
- synthetic SDN dataset generator
- RandomForest traffic-state classifier
- RandomForest SLA-risk regressor
- policy agent that queries Prometheus and issues controller actions

### SDN controller integration
Implemented through:
- Ryu topology-aware forwarding
- REST policy endpoint
- dynamic block and reroute actions
- mitigation expiry and cleanup

## Expected outcomes supported by the codebase
- real-time monitoring and visualization,
- ML-based anomaly and congestion prediction,
- adaptive SDN policy enforcement,
- a closed feedback loop between telemetry and control.

## Suggested future work
- replace the synthetic training set with public SDN traffic datasets,
- add deep learning or reinforcement learning,
- integrate OpenDaylight or ONOS for multi-controller comparison,
- introduce QoS queues and meter-table actions for fine-grained rate limiting.
