import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    import app as app_module

    flask_app.config["TESTING"] = True
    app_module._request_log.clear()  # rate limiter state is process-global; reset per test
    with flask_app.test_client() as c:
        yield c


def _mock_reply(text="mocked reply"):
    """Patch get_ai_response so no network/API key is needed in route tests."""
    return patch("app.get_ai_response", return_value=text)


# --- pages -------------------------------------------------------------
def test_index_page_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"StadiumGenie" in res.data


def test_ops_page_loads(client):
    res = client.get("/ops")
    assert res.status_code == 200
    assert b"Ops" in res.data


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


# --- security headers ----------------------------------------------------
def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in res.headers


# --- fan chat endpoint -----------------------------------------------------
def test_chat_success(client):
    with _mock_reply("The nearest restroom is 20m away."):
        res = client.post("/api/chat", json={"message": "Where's the restroom?", "section": "203"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["reply"] == "The nearest restroom is 20m away."
    assert "context_used" in data


def test_chat_rejects_empty_message(client):
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_chat_rejects_non_string_section(client):
    res = client.post("/api/chat", json={"message": "hi", "section": 123})
    assert res.status_code == 400


def test_chat_handles_missing_body(client):
    res = client.post("/api/chat", json={})
    assert res.status_code == 400


def test_chat_ai_service_failure_returns_503(client):
    with patch("app.get_ai_response", side_effect=__import__("exceptions").AIServiceError("down")):
        res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 503


def test_chat_rate_limit_enforced(client):
    with _mock_reply():
        for _ in range(20):
            res = client.post("/api/chat", json={"message": "hi"})
            assert res.status_code == 200
        res = client.post("/api/chat", json={"message": "one too many"})
    assert res.status_code == 429


# --- emergency exit endpoint ------------------------------------------------
def test_emergency_exit_known_gate(client):
    res = client.get("/api/emergency-exit/A")
    assert res.status_code == 200
    assert "Gate A" in res.get_json()["emergency_exit"]


def test_emergency_exit_unknown_gate(client):
    res = client.get("/api/emergency-exit/Z")
    assert res.status_code == 404


# --- ops chat endpoint -------------------------------------------------
def test_ops_chat_success(client):
    with _mock_reply("Gate C is at 91% capacity, recommend metering entry."):
        res = client.post("/api/ops/chat", json={"message": "Status at Gate C?", "gate": "C"})
    assert res.status_code == 200
    assert "Gate C" in res.get_json()["reply"]


def test_ops_chat_rejects_empty_message(client):
    res = client.post("/api/ops/chat", json={"message": ""})
    assert res.status_code == 400


# --- incident logging ----------------------------------------------------
def test_create_incident_success(client):
    res = client.post(
        "/api/ops/incidents",
        json={
            "gate": "C",
            "category": "crowd_surge",
            "severity": "high",
            "description": "Queue backing up",
        },
    )
    assert res.status_code == 201
    incident = res.get_json()["incident"]
    assert incident["gate"] == "C"
    assert incident["resolved"] is False


def test_create_incident_invalid_category(client):
    res = client.post(
        "/api/ops/incidents",
        json={
            "gate": "C",
            "category": "not_a_real_category",
            "severity": "high",
            "description": "x",
        },
    )
    assert res.status_code == 400


def test_create_incident_invalid_severity(client):
    res = client.post(
        "/api/ops/incidents",
        json={"gate": "C", "category": "medical", "severity": "extreme", "description": "x"},
    )
    assert res.status_code == 400


def test_create_incident_missing_gate(client):
    res = client.post(
        "/api/ops/incidents",
        json={"gate": "", "category": "medical", "severity": "low", "description": "x"},
    )
    assert res.status_code == 400


def test_list_and_resolve_incident(client):
    create_res = client.post(
        "/api/ops/incidents",
        json={
            "gate": "D",
            "category": "facility",
            "severity": "low",
            "description": "Spill near Gate D",
        },
    )
    incident_id = create_res.get_json()["incident"]["id"]

    list_res = client.get("/api/ops/incidents?gate=D&unresolved_only=true")
    assert list_res.status_code == 200
    assert any(i["id"] == incident_id for i in list_res.get_json()["incidents"])

    resolve_res = client.post(f"/api/ops/incidents/{incident_id}/resolve")
    assert resolve_res.status_code == 200
    assert resolve_res.get_json()["resolved"] is True


def test_resolve_nonexistent_incident(client):
    res = client.post("/api/ops/incidents/999999/resolve")
    assert res.status_code == 404


# --- request size cap ----------------------------------------------------
def test_oversized_request_rejected(client):
    huge_payload = {"message": "a" * 20000}
    res = client.post("/api/chat", json=huge_payload)
    assert res.status_code == 413
