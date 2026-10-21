from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_reports_alive() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_does_not_claim_database_was_probed() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["configuration"] == "valid"
    assert body["checks"]["database"] in {"configured_not_probed", "not_configured_yet"}
