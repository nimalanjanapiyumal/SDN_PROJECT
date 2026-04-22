# Testing and Evaluation

## Functional integration
In Mininet:
```bash
h1 ping -c 2 10.0.0.100
h1 curl http://10.0.0.100:8000
```
Expected result: VIP reachable and backend JSON response visible.

## Performance and scalability
```bash
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 10 --duration 20 --sla-ms 200 --json /tmp/http_10.json
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 20 --duration 20 --sla-ms 200 --json /tmp/http_20.json
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 50 --duration 20 --sla-ms 200 --json /tmp/http_50.json
```
Upload the JSON files on the dashboard Testing page.

## Traffic throughput
```bash
h2 iperf3 -s -p 5201 &
h3 iperf3 -s -p 5201 &
h4 iperf3 -s -p 5201 &
h1 python3 tools/iperf3_benchmark.py --vip 10.0.0.100 --port 5201 --duration 15 --parallel 4 --json /tmp/iperf_4.json
```

## Fault tolerance
Use dashboard health buttons or call the controller API:
```bash
curl -X POST http://<controller-ip>:8080/lb/health/srv1 -H 'Content-Type: application/json' -d '{"healthy": false}'
```
Then rerun curl and benchmark tests.

## Prometheus note
Prometheus is optional. Even without it, the controller already exposes flow count and bandwidth-derived metrics using OpenFlow port statistics. Prometheus adds CPU and memory utilization per backend when you map exporter instances in `config.controller.yaml`.
