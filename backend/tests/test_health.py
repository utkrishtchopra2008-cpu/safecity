from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_reports_alive() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_reports_database_not_configured_without_claiming_ready() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["configuration"] == "valid"
    assert body["checks"]["database"] == "not_configured"
    assert body["checks"]["worker"] == "not_reported"
