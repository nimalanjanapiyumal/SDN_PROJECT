# REST API specification

Base URL: `http://<controller-host>:8080`

All payloads are JSON. Error responses use the standard FastAPI shape:
`{"detail": "..."}` with a 4xx status.

## Health

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET    | `/healthz` | Liveness probe |

## Intent

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST   | `/api/intent/submit` | Validate + rank + install an intent |
| GET    | `/api/intent/list`   | All registered intents |
| DELETE | `/api/intent/{id}`   | Remove the intent and its flow records |

`POST /api/intent/submit` request:

```json
{
  "intent_type": "security",
  "action": "block",
  "src_ip": "10.0.0.5",
  "dst_ip": "10.0.0.10",
  "priority": 10
}
```

Response (201):

```json
{
  "intent": { "...": "validated intent" },
  "translated": {
    "flow_action": "drop",
    "match": { "eth_type": 2048, "ipv4_src": "10.0.0.5", "ipv4_dst": "10.0.0.10" },
    "priority": 60,
    "metadata": { "intent_type": "security", "action": "block" }
  },
  "ranking": { "intent_id": "...", "final_priority": 60, "boost": 50 },
  "records": [ { "rule_id": "...", "dpid": 0, "...": "..." } ]
}
```

## Context

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/context/update`        | Push monitoring/threat/SLA context |
| GET  | `/api/context/current`       | Retrieve current context + last ML prediction |
| POST | `/api/context/ml-prediction` | Forward an ML prediction to the controller |

`POST /api/context/update` body:

```json
{
  "threat": "high",
  "congestion": "medium",
  "sla_risk": "low",
  "latency_ms": 130,
  "packet_loss": 1.5,
  "cpu_usage": 70,
  "memory_usage": 60
}
```

## Network

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET    | `/api/network/hosts`    | All learned hosts |
| GET    | `/api/network/topology` | Switches + links |
| GET    | `/api/flow/list`        | All recorded flow rules |
| POST   | `/api/flow/install`     | Install a custom flow rule |
| POST   | `/api/flow/delete`      | Remove by `rule_id` or `intent_id` |
