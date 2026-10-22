import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import AppSettings
from app.db.models import ExternalContextItem, ProcessingJob, Source
from app.services import context_jobs
from app.services.tinyfish import FetchResult, SearchResult


def _factory() -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _: connection.create_function(
            "jsonb_typeof", 1, lambda value: "object" if value.startswith("{") else "array"
        ),
    )
    for table in (Source.__table__, ProcessingJob.__table__, ExternalContextItem.__table__):
        table.create(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def test_source_context_job_persists_bounded_attributed_items_idempotently(
    monkeypatch,
) -> None:
    factory, engine = _factory()
    source_id, first_job_id, second_job_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    with factory() as database:
        database.add(
            Source(
                id=source_id,
                name="Downtown demo source",
                source_type="simulated",
                status="ready",
                context_area_label="Downtown",
                context_retrieval_enabled=True,
                configuration={"context_topics": ["public_notice"]},
            )
        )
        for job_id in (first_job_id, second_job_id):
            database.add(
                ProcessingJob(
                    id=job_id,
                    job_type="context_enrichment",
                    source_id=source_id,
                    status="running",
                    attempt_count=1,
                    max_attempts=3,
                    available_at=now,
                    result_metadata={"topics": ["public_notice"], "time_window_hours": 24},
                )
            )
        database.commit()

    async def fake_search(_settings, query: str, *, topic: str, recency_minutes: int | None):
        assert query == "Downtown public notice"
        assert topic == "public_notice"
        assert recency_minutes == 1440
        return [
            SearchResult(
                title="Notice title",
                snippet="Search snippet is not persisted.",
                publisher="City Office",
                source_domain="example.gov",
                source_url="https://example.gov/notices/public",
                published_at=None,
                retrieved_at=now,
                freshness="unknown",
            )
        ]

    async def fake_fetch(_settings, public_url: str):
        assert public_url == "https://example.gov/notices/public"
        return FetchResult(
            title="Notice title",
            description=None,
            text="Fetched public excerpt.",
            publisher="City Office",
            source_domain="example.gov",
            source_url=public_url,
            published_at=None,
            retrieved_at=now,
            freshness="unknown",
        )

    monkeypatch.setattr(context_jobs, "search_public_context", fake_search)
    monkeypatch.setattr(context_jobs, "fetch_public_context", fake_fetch)
    provider_settings = AppSettings(
        tinyfish_context_enabled=True,
        tinyfish_api_key="mock-only-key",
        tinyfish_allowed_domains=["example.gov"],
    )

    asyncio.run(
        context_jobs.process_context_job(factory, provider_settings, first_job_id, source_id)
    )
    asyncio.run(
        context_jobs.process_context_job(factory, provider_settings, second_job_id, source_id)
    )

    with factory() as database:
        items = list(database.scalars(select(ExternalContextItem)))
        assert len(items) == 1
        assert items[0].summary == "Fetched public excerpt."
        assert "Search snippet" not in items[0].summary
        assert items[0].provider_metadata == {"provider": "tinyfish", "format": "markdown"}
        completed = database.get(ProcessingJob, second_job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.result_metadata["context_result_count"] == 1
        source = database.get(Source, source_id)
        assert source is not None
        assert source.status == "ready"
    engine.dispose()
