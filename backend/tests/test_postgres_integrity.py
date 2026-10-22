"""Opt-in integration checks against a disposable, already migrated PostgreSQL database."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

TEST_DATABASE_URL = os.environ.get("SAFECITY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="SAFECITY_TEST_DATABASE_URL must point to a disposable migrated PostgreSQL database",
)


def test_postgres_constraints_concurrent_idempotency_and_rollback() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    source_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO sources (id, name, source_type, status) VALUES (:id, 'integration', 'simulated', 'ready')"
            ),
            {"id": source_id},
        )

    def ingest_same_event() -> bool:
        try:
            with engine.begin() as connection:
                connection.execute(
                    text("""INSERT INTO incidents
                    (id, source_id, source_event_id, detection_category, detector_name)
                    VALUES (:id, :source_id, 'duplicate-test', 'fixture', 'test')"""),
                    {"id": uuid4(), "source_id": source_id},
                )
            return True
        except IntegrityError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        inserted = list(executor.map(lambda _: ingest_same_event(), range(2)))
    assert sorted(inserted) == [False, True]

    with engine.begin() as connection:
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text("""INSERT INTO incidents
                (id, source_id, event_start_at, event_end_at, detection_category, detector_name)
                VALUES (:id, :source_id, '2026-01-02T00:00:00Z', '2026-01-01T00:00:00Z', 'fixture', 'test')"""),
                {"id": uuid4(), "source_id": source_id},
            )

    rollback_id = uuid4()
    with pytest.raises(RuntimeError, match="rollback fixture"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO sources (id, name, source_type, status) VALUES (:id, 'rollback', 'simulated', 'ready')"
                ),
                {"id": rollback_id},
            )
            raise RuntimeError("rollback fixture")
    with engine.begin() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM sources WHERE id = :id"), {"id": rollback_id}
            )
            == 0
        )
        connection.execute(text("DELETE FROM incidents WHERE source_id = :id"), {"id": source_id})
        connection.execute(text("DELETE FROM sources WHERE id = :id"), {"id": source_id})
        audit_id = uuid4()
        connection.execute(
            text("""INSERT INTO audit_events
            (id, actor_role, action, object_type, result)
            VALUES (:id, 'anonymous', 'auth.login', 'authentication', 'denied')"""),
            {"id": audit_id},
        )

    for statement in (
        "UPDATE audit_events SET result = 'success' WHERE id = :id",
        "DELETE FROM audit_events WHERE id = :id",
    ):
        with engine.begin() as connection:
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(text(statement), {"id": audit_id})
    engine.dispose()
