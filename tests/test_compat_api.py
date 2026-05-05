import pytest

from adaptive_cloud_platform.app import app, operator_auth_service


@pytest.fixture()
def client():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_compat_intent_submit_accepts_form_data(client):
    response = client.post("/api/intent/submit", data={
        "intent_type": "security",
        "intent": "Block suspicious traffic from 10.0.0.5",
        "src_ip": "10.0.0.5",
        "dst_ip": "10.0.0.10",
        "port": "443",
        "priority": "10",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["component_3_translation"]["classification"]["type"] == "security"


def test_compat_context_update_accepts_form_data(client):
    response = client.post("/api/context/update", data={
        "source": "monitoring",
        "threat": "high",
        "congestion": "medium",
        "latency_ms": "125",
        "controller_cpu_percent": "82",
        "packet_in_rate_per_sec": "260",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert "component_2_prediction" in payload


def test_compat_flow_install_and_delete_accept_form_data(client):
    install = client.post("/api/flow/install", data={
        "src_ip": "10.0.0.5",
        "dst_ip": "10.0.0.10",
        "flow_action": "drop",
        "priority": "120",
        "switch": "s2",
    })
    assert install.status_code == 200
    install_payload = install.json()
    assert install_payload["accepted"] is True
    rule_id = install_payload["rule"]["id"]

    delete = client.post("/api/flow/delete", data={"rule_id": rule_id})
    assert delete.status_code == 200
    delete_payload = delete.json()
    assert delete_payload["accepted"] is True
    assert delete_payload["removed"] == 1


def test_compat_ml_predict_accepts_form_data(client):
    response = client.post("/api/ml/predict", data={
        "latency_ms": "140",
        "controller_cpu_percent": "84",
        "controller_memory_percent": "72",
        "packet_in_rate_per_sec": "280",
        "max_link_utilization_ratio": "0.91",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert "prediction" in payload


def test_compat_operator_login_and_verify_accept_form_data(client):
    login = client.post("/api/v1/auth/login", data={"username": "admin", "pw": "admin123"})
    assert login.status_code == 200
    login_payload = login.json()
    assert login_payload["otp_required"] is True

    verify = client.post("/api/v1/auth/verify-otp", data={
        "challengeId": login_payload["challenge_id"],
        "otp": operator_auth_service.current_otp_code_for_testing(),
    })
    assert verify.status_code == 200
    verify_payload = verify.json()
    assert verify_payload["authenticated"] is True


def test_compat_security_session_login_accepts_form_data(client):
    response = client.post("/auth/login", data={
        "username": "admin",
        "src_ip": "10.0.0.2",
        "pw": "admin123",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True

