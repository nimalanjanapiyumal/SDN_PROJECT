"""End-to-end tests of the FastAPI surface."""
from __future__ import annotations

from fastapi.testclient import TestClient

from sdn_adaptive_cloud_framework.api import create_app
from sdn_adaptive_cloud_framework.controller import reset_state_for_tests


def _client() -> TestClient:
    reset_state_for_tests()
    return TestClient(create_app())


def test_healthz():
    r = _client().get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_submit_intent_and_listing():
    client = _client()
    r = client.post("/api/intent/submit", json={
        "intent_type": "security", "action": "block",
        "src_ip": "10.0.0.5", "dst_ip": "10.0.0.10", "priority": 100,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["translated"]["flow_action"] == "drop"
    intent_id = body["intent"]["intent_id"]

    r = client.get("/api/intent/list")
    assert r.status_code == 200
    assert any(i["intent_id"] == intent_id for i in r.json()["intents"])

    r = client.delete(f"/api/intent/{intent_id}")
    assert r.status_code == 200


def test_context_update_changes_priority():
    client = _client()
    client.post("/api/intent/submit", json={
        "intent_type": "load_balancing", "action": "balance",
        "src_ip": "10.0.0.5",
    })
    r = client.post("/api/context/update", json={"congestion": "high"})
    assert r.status_code == 200
    assert r.json()["context"]["congestion"] == "high"

    r = client.get("/api/context/current")
    assert r.json()["context"]["congestion"] == "high"


def test_flow_install_and_delete():
    client = _client()
    r = client.post("/api/flow/install", json={
        "match": {"eth_type": 0x0800, "ipv4_src": "10.0.0.42"},
        "flow_action": "drop", "priority": 200,
    })
    assert r.status_code == 200
    rule_id = r.json()["records"][0]["rule_id"]

    r = client.post("/api/flow/delete", json={"rule_id": rule_id})
    assert r.status_code == 200


def test_invalid_intent_returns_400():
    client = _client()
    r = client.post("/api/intent/submit", json={
        "intent_type": "security", "action": "balance",  # invalid combo
    })
    assert r.status_code == 400


def test_topology_and_hosts_empty_initially():
    client = _client()
    assert client.get("/api/network/topology").json() == {"switches": [], "links": []}
    assert client.get("/api/network/hosts").json() == {"hosts": []}
