import hashlib
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import public_context as public_context_api
from app.api.v1.auth import COOKIE_NAME, login_limiter
from app.core.config import AppSettings, get_settings
from app.db.models import AuditEvent, Session, User
from app.db.session import get_db
from app.main import app
from app.services.tinyfish import FetchResult, SearchResult


@pytest.fixture
def auth_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    Session.__table__.create(engine)
    AuditEvent.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    test_settings = AppSettings(
        app_env="test",
        public_app_origin="http://testserver",
        csrf_allowed_origins=["http://testserver"],
        session_csrf_secret="test-csrf-secret-at-least-32-characters",
    )

    def override_db() -> Generator[OrmSession, None, None]:
        with factory() as database:
            yield database

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.state.test_session_factory = factory
    with factory() as database:
        database.add(
            User(
                id=uuid.uuid4(),
                email="operator@example.com",
                display_name="Test Operator",
                password_hash=PasswordHasher().hash("correct horse battery staple"),
                role="operator",
                is_active=True,
            )
        )
        database.commit()
    login_limiter._attempts.clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    del app.state.test_session_factory
    engine.dispose()


def test_login_sets_httponly_session_and_never_returns_token(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "OPERATOR@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert "session_token" not in response.text
    assert "token_hash" not in response.text
    assert response.json()["user"]["role"] == "operator"
    cookie = response.headers["set-cookie"]
    assert f"{COOKIE_NAME}=" in cookie
    assert "httponly" in cookie.lower()
    assert "path=/api/v1" in cookie.lower()


def test_invalid_credentials_are_generic_and_do_not_issue_cookie(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.json()["detail"] == "Email or password is incorrect."
    assert "set-cookie" not in response.headers


def test_logout_requires_csrf_and_revokes_session(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200

    denied = auth_client.post("/api/v1/auth/logout", headers={"Origin": "http://testserver"})
    assert denied.status_code == 403

    csrf = auth_client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200
    logged_out = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf.json()["csrf_token"]},
    )
    assert logged_out.status_code == 204
    assert auth_client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("invalid_state", ["expired", "revoked"])
def test_expired_or_revoked_session_is_rejected(
    auth_client: TestClient, invalid_state: str
) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    raw_token = auth_client.cookies.get(COOKIE_NAME)
    assert raw_token
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    factory = auth_client.app.state.test_session_factory
    with factory() as database:
        record = database.query(Session).filter_by(token_hash=token_hash).one()
        if invalid_state == "expired":
            record.created_at = datetime(1999, 1, 1, tzinfo=UTC)
            record.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
        else:
            record.revoked_at = datetime.now(UTC)
        database.commit()

    assert auth_client.get("/api/v1/auth/me").status_code == 401


def test_csrf_rejects_untrusted_origin(auth_client: TestClient) -> None:
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    csrf = auth_client.get("/api/v1/auth/csrf").json()["csrf_token"]

    response = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://attacker.example", "X-CSRF-Token": csrf},
    )

    assert response.status_code == 403


def test_login_rate_limit_returns_retry_after(auth_client: TestClient) -> None:
    payload = {"email": "operator@example.com", "password": "incorrect"}
    for _ in range(10):
        auth_client.post("/api/v1/auth/login", json=payload)

    response = auth_client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 429
    assert response.headers["retry-after"]


def test_incident_routes_are_registered_and_require_authentication(
    auth_client: TestClient,
) -> None:
    listing = auth_client.get("/api/v1/incidents")
    review = auth_client.post(
        f"/api/v1/incidents/{uuid.uuid4()}/reviews",
        json={"outcome": "confirmed"},
    )

    assert listing.status_code == 401
    assert listing.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert review.status_code == 401
    assert review.json()["code"] == "AUTHENTICATION_REQUIRED"


def test_source_mutation_rejects_operator_role(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    response = auth_client.post(
        "/api/v1/sources",
        headers={"Origin": "http://testserver"},
        json={"name": "Test source", "source_type": "simulated"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


def test_job_and_system_routes_are_registered_and_require_authentication(
    auth_client: TestClient,
) -> None:
    job = auth_client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    status = auth_client.get("/api/v1/system/status")

    assert job.status_code == 401
    assert status.status_code == 401


def test_source_detail_and_processing_routes_require_authentication(
    auth_client: TestClient,
) -> None:
    source_id = uuid.uuid4()
    detail = auth_client.get(f"/api/v1/sources/{source_id}")
    process = auth_client.post(f"/api/v1/sources/{source_id}/process")
    context = auth_client.get(f"/api/v1/sources/{source_id}/context")
    refresh = auth_client.post(f"/api/v1/sources/{source_id}/context-refresh")

    assert detail.status_code == 401
    assert process.status_code == 401
    assert context.status_code == 401
    assert refresh.status_code == 401


def test_operator_can_list_sources_and_missing_source_is_not_found(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200

    class EmptySourceQuery:
        def order_by(self, *_args):
            return self

        def limit(self, _count):
            return []

    factory = auth_client.app.state.test_session_factory

    class ReadOnlyDatabase:
        def __init__(self, database: OrmSession) -> None:
            self.database = database

        def __getattr__(self, name):
            return getattr(self.database, name)

        def execute(self, *args, **kwargs):
            return self.database.execute(*args, **kwargs)

        def query(self, _model):
            return EmptySourceQuery()

        def get(self, _model, _source_id):
            return None

    def empty_source_db() -> Generator[ReadOnlyDatabase, None, None]:
        with factory() as database:
            yield ReadOnlyDatabase(database)

    monkeypatch.setitem(app.dependency_overrides, get_db, empty_source_db)

    listing = auth_client.get("/api/v1/sources")
    detail = auth_client.get(f"/api/v1/sources/{uuid.uuid4()}")

    assert listing.status_code == 200
    assert listing.json() == []
    assert detail.status_code == 404
    assert detail.json()["code"] == "RESOURCE_NOT_FOUND"


def test_operator_can_read_owned_job_without_sensitive_diagnostics(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    user_id = uuid.UUID(login.json()["user"]["id"])
    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    job = SimpleNamespace(
        id=job_id,
        created_by=user_id,
        job_type="source_processing",
        status="failed",
        created_at=now,
        started_at=now,
        finished_at=now,
        attempt_count=2,
        error_code="INTERNAL_PATH_DISCLOSED",
        error_summary="Sensitive provider diagnostic",
        result_metadata={"duration_seconds": 1.5, "private_path": "/srv/private/video.mp4"},
    )

    factory = auth_client.app.state.test_session_factory

    class JobDatabase:
        def __init__(self, database: OrmSession) -> None:
            self.database = database

        def __getattr__(self, name):
            return getattr(self.database, name)

        def get(self, _model, requested_id):
            return job if requested_id == job_id else None

    def job_db() -> Generator[JobDatabase, None, None]:
        with factory() as database:
            yield JobDatabase(database)

    monkeypatch.setitem(app.dependency_overrides, get_db, job_db)

    response = auth_client.get(f"/api/v1/jobs/{job_id}")
    hidden_job = auth_client.get(f"/api/v1/jobs/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json()["result_metadata"] == {"duration_seconds": 1.5}
    assert response.json()["error_code"] is None
    assert response.json()["error_summary"] is None
    assert hidden_job.status_code == 404
    assert hidden_job.json()["code"] == "RESOURCE_NOT_FOUND"


def test_reliability_route_requires_authentication(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/reliability/summary")

    assert response.status_code == 401


def test_dashboard_route_requires_authentication(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401


def test_evaluation_routes_require_authentication(auth_client: TestClient) -> None:
    listing = auth_client.get("/api/v1/evaluations")
    detail = auth_client.get(f"/api/v1/evaluations/{uuid.uuid4()}")
    create = auth_client.post(
        "/api/v1/evaluations",
        headers={"Origin": "http://testserver"},
        json={"dataset_id": str(uuid.uuid4()), "detector_name": "unknown"},
    )

    assert listing.status_code == 401
    assert detail.status_code == 401
    assert create.status_code == 401


def test_public_context_search_requires_authentication(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/public-context/search",
        headers={"Origin": "http://testserver"},
        json={"query": "public transport advisory", "topic": "transport_disruption"},
    )

    assert response.status_code == 401


def test_public_context_search_uses_backend_provider_and_returns_provenance(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_search(_settings, query: str, *, topic: str) -> list[SearchResult]:
        assert query == "public transport advisory"
        assert topic == "transport_disruption"
        now = datetime.now(UTC)
        return [
            SearchResult(
                title="Transit notice",
                snippet="Route changes are posted.",
                publisher="Public Transit",
                source_domain="example.gov",
                source_url="https://example.gov/notices/route",
                published_at=None,
                retrieved_at=now,
                freshness="unknown",
            )
        ]

    monkeypatch.setattr(public_context_api, "search_public_context", fake_search)

    async def fake_fetch(_settings, public_url: str) -> FetchResult:
        assert public_url == "https://example.gov/notices/route"
        return FetchResult(
            title="Transit notice",
            description=None,
            text="Public source excerpt.",
            publisher="example.gov",
            source_domain="example.gov",
            source_url=public_url,
            published_at=None,
            retrieved_at=datetime.now(UTC),
            freshness="unknown",
        )

    monkeypatch.setattr(public_context_api, "fetch_public_context", fake_fetch)
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct horse battery staple"},
    )
    csrf = auth_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = auth_client.post(
        "/api/v1/public-context/search",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
        json={"query": "public transport advisory", "topic": "transport_disruption"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "available"
    assert payload["results"][0]["source_domain"] == "example.gov"
    assert payload["results"][0]["freshness"] == "unknown"
    assert "does not verify" in payload["note"]
    unlisted = auth_client.post(
        "/api/v1/public-context/fetch",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
        json={"source_url": "https://example.gov/notices/other"},
    )
    assert unlisted.status_code == 422
    fetch = auth_client.post(
        "/api/v1/public-context/fetch",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
        json={"source_url": "https://example.gov/notices/route"},
    )
    assert fetch.status_code == 200
    assert fetch.json()["text"] == "Public source excerpt."


def test_evidence_metadata_and_content_routes_require_authentication(
    auth_client: TestClient,
) -> None:
    evidence_id = uuid.uuid4()
    metadata = auth_client.get(f"/api/v1/evidence/{evidence_id}")
    content = auth_client.get(f"/api/v1/evidence/{evidence_id}/content")

    assert metadata.status_code == 401
    assert content.status_code == 401
