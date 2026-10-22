"""Asynchronous source-context refresh handler with short DB transactions."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from app.core.config import AppSettings
from app.db.models import ExternalContextItem, ProcessingJob, Source
from app.services.tinyfish import TinyFishUnavailable, fetch_public_context, search_public_context

logger = logging.getLogger("safecity.context")
ALLOWED_TOPICS = {
    "weather_advisory",
    "transport_disruption",
    "public_notice",
    "public_event",
    "emergency_advisory",
    "other",
}
MAX_CONTEXT_TOPICS_PER_JOB = 3
MAX_FETCHES_PER_JOB = 5
MAX_CONTEXT_SECONDS = 150


async def process_context_job(
    factory: sessionmaker[OrmSession], settings: AppSettings, job_id: UUID, source_id: UUID
) -> None:
    """Perform public Search/Fetch outside transactions, then idempotently persist attribution."""
    with factory() as database:
        job = database.get(ProcessingJob, job_id)
        source = database.get(Source, source_id)
        if job is None or job.status != "running" or source is None:
            return
        requested_topics = job.result_metadata.get("topics")
        time_window_hours = job.result_metadata.get("time_window_hours")
        approved_topics = source.configuration.get("context_topics")
        area = source.context_area_label
        enabled = source.context_retrieval_enabled
        if (
            not enabled
            or not isinstance(area, str)
            or not isinstance(requested_topics, list)
            or not isinstance(approved_topics, list)
            or not requested_topics
            or not isinstance(time_window_hours, int)
            or not 1 <= time_window_hours <= 168
            or len(requested_topics) > MAX_CONTEXT_TOPICS_PER_JOB
            or any(
                topic not in ALLOWED_TOPICS or topic not in approved_topics
                for topic in requested_topics
            )
        ):
            raise ValueError("CONTEXT_CONFIGURATION_INVALID")

    started = time.monotonic()
    collected: list[dict[str, Any]] = []
    fetch_failures = 0
    fetch_count = 0
    try:
        async with asyncio.timeout(MAX_CONTEXT_SECONDS):
            for topic in requested_topics:
                query = f"{area} {topic.replace('_', ' ')}"
                search_results = await search_public_context(
                    settings,
                    query,
                    topic=topic,
                    recency_minutes=time_window_hours * 60,
                )
                for search_result in search_results:
                    if fetch_count >= MAX_FETCHES_PER_JOB:
                        break
                    fetch_count += 1
                    try:
                        fetched = await fetch_public_context(settings, search_result.source_url)
                    except (TinyFishUnavailable, ValueError):
                        fetch_failures += 1
                        continue
                    digest = hashlib.sha256(
                        "|".join(
                            (
                                topic,
                                fetched.source_url,
                                fetched.title,
                                fetched.published_at.isoformat() if fetched.published_at else "",
                            )
                        ).encode("utf-8")
                    ).hexdigest()
                    retrieved_at = fetched.retrieved_at
                    collected.append(
                        {
                            "id": uuid.uuid4(),
                            "source_id": source_id,
                            "processing_job_id": job_id,
                            "topic": topic,
                            "title": fetched.title,
                            "publisher": fetched.publisher,
                            "source_domain": fetched.source_domain,
                            "source_url": fetched.source_url,
                            "summary": fetched.text[:1_200],
                            "published_at": fetched.published_at,
                            "retrieved_at": retrieved_at,
                            "stale_after": (
                                fetched.published_at
                                + timedelta(seconds=settings.tinyfish_context_ttl_seconds)
                                if fetched.published_at
                                else None
                            ),
                            "dedupe_key": digest,
                            "provider_metadata": {"provider": "tinyfish", "format": "markdown"},
                        }
                    )
    except (TimeoutError, TinyFishUnavailable) as exc:
        raise ValueError("CONTEXT_PROVIDER_UNAVAILABLE") from exc

    with factory() as database, database.begin():
        job = database.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
        )
        if job is None or job.status != "running":
            return
        if collected:
            dialect = database.get_bind().dialect.name
            statement: Any
            if dialect == "postgresql":
                statement = (
                    pg_insert(ExternalContextItem)
                    .values(collected)
                    .on_conflict_do_nothing(constraint="uq_context_source_dedupe")
                )
            elif dialect == "sqlite":
                statement = (
                    sqlite_insert(ExternalContextItem)
                    .values(collected)
                    .on_conflict_do_nothing(index_elements=["source_id", "dedupe_key"])
                )
            else:
                raise RuntimeError("unsupported_context_database_dialect")
            database.execute(statement)
        job.status = "completed"
        job.finished_at = datetime.now(UTC)
        job.heartbeat_at = job.finished_at
        job.lease_expires_at = None
        job.result_metadata = {
            **job.result_metadata,
            "context_result_count": len(collected),
            "context_fetch_failures": fetch_failures,
            "context_refresh_status": "partial" if fetch_failures else "complete",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    logger.info(
        "context_job_completed job_id=%s source_id=%s result_count=%s fetch_failures=%s",
        job_id,
        source_id,
        len(collected),
        fetch_failures,
    )
