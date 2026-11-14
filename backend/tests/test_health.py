"""Health endpoint behaviour, including the unconfigured-service path."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root_advertises_docs(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_supabase_probe_reports_503_when_unconfigured(client: TestClient) -> None:
    response = client.get("/health/supabase")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()
