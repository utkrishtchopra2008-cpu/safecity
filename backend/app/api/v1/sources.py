"""Source registration and bounded video-upload routes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, require_csrf, require_roles
from app.core.config import AppSettings, get_settings
from app.core.rate_limit import SlidingWindowLimiter
from app.db.models import Evidence, ExternalContextItem, ProcessingJob, Source
from app.db.session import get_db
from app.media.uploads import UploadTooLarge, UploadValidationError, stage_video_upload
from app.services.audit import record_security_event
from app.storage.supabase import StorageUnavailable, SupabaseStorage

router = APIRouter(prefix="/sources", tags=["sources"])
source_create_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
source_process_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)


def _enforce_user_limit(limiter: SlidingWindowLimiter, user_id: UUID) -> None:
    retry_after = limiter.check(str(user_id))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Please wait before starting another source operation.",
            headers={"Retry-After": str(retry_after)},
        )


class SimulatedSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source_type: str = "simulated"
    configuration: dict[str, str | int | float | bool] = Field(default_factory=dict)
    context_area_label: str | None = Field(default=None, max_length=160)
    context_retrieval_enabled: bool = False
    context_topics: list[
        Literal[
            "weather_advisory",
            "transport_disruption",
            "public_notice",
            "public_event",
            "emergency_advisory",
            "other",
        ]
    ] = Field(default_factory=list, max_length=3)


class SourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    status: str
    created_at: datetime
    last_processed_at: datetime | None
    context_area_label: str | None
    context_retrieval_enabled: bool


class UploadAccepted(BaseModel):
    source_id: str
    evidence_id: str
    job_id: str
    status: str


class ProcessingAccepted(BaseModel):
    source_id: str
    job_id: str
    status: str


class ContextRefreshRequest(BaseModel):
    topics: list[
        Literal[
            "weather_advisory",
            "transport_disruption",
            "public_notice",
            "public_event",
            "emergency_advisory",
            "other",
        ]
    ] = Field(default_factory=list, max_length=3)
    time_window_hours: int = Field(default=24, ge=1, le=168)


class ContextRefreshAccepted(BaseModel):
    source_id: UUID
    job_id: UUID
    status: Literal["pending"]


class ContextItemResponse(BaseModel):
    id: UUID
    topic: str
    title: str
    publisher: str | None
    source_domain: str
    source_url: str
    summary: str
    published_at: datetime | None
    retrieved_at: datetime
    freshness_status: Literal["current", "stale", "unknown"]
    processing_job_id: UUID


class ContextItemPage(BaseModel):
    items: list[ContextItemResponse]
    page: int
    page_size: int
    has_more: bool


@router.get("", response_model=list[SourceResponse])
def list_sources(
    _context: AuthContext = Depends(require_roles("operator", "supervisor", "technical_admin")),
    database: OrmSession = Depends(get_db),
) -> list[SourceResponse]:
    rows = database.query(Source).order_by(Source.created_at.desc(), Source.id.desc()).limit(200)
    return [
        SourceResponse(
            id=str(item.id),
            name=item.name,
            source_type=item.source_type,
            status=item.status,
            created_at=item.created_at,
            last_processed_at=item.last_processed_at,
            context_area_label=item.context_area_label,
            context_retrieval_enabled=item.context_retrieval_enabled,
        )
        for item in rows
    ]


@router.get("/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: UUID,
    _context: AuthContext = Depends(require_roles("operator", "supervisor", "technical_admin")),
    database: OrmSession = Depends(get_db),
) -> SourceResponse:
    source = database.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at,
        last_processed_at=source.last_processed_at,
        context_area_label=source.context_area_label,
        context_retrieval_enabled=source.context_retrieval_enabled,
    )


@router.post("", response_model=SourceResponse, status_code=201)
def register_simulated_source(
    body: SimulatedSourceCreate,
    request: Request,
    context: AuthContext = Depends(require_roles("technical_admin")),
    _csrf: AuthContext = Depends(require_csrf),
    database: OrmSession = Depends(get_db),
) -> SourceResponse:
    _enforce_user_limit(source_create_limiter, context.user.id)
    if body.source_type != "simulated":
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    if body.context_retrieval_enabled and not body.context_area_label:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    if body.context_retrieval_enabled and not body.context_topics:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    if body.context_area_label and not all(
        char.isalpha() or char.isspace() or char in "-," for char in body.context_area_label
    ):
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    safe_configuration: dict[str, Any] = dict(body.configuration)
    safe_configuration["demo_fixture_flow"] = True
    safe_configuration["context_topics"] = body.context_topics
    source = Source(
        name=body.name.strip(),
        source_type="simulated",
        status="ready",
        context_area_label=body.context_area_label,
        context_retrieval_enabled=body.context_retrieval_enabled,
        configuration=safe_configuration,
        created_by=context.user.id,
    )
    database.add(source)
    record_security_event(
        database,
        request,
        action="source.create",
        result="success",
        actor=context.user,
        object_type="source",
        object_id=str(source.id),
    )
    database.commit()
    database.refresh(source)
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at,
        last_processed_at=source.last_processed_at,
        context_area_label=source.context_area_label,
        context_retrieval_enabled=source.context_retrieval_enabled,
    )


@router.get("/{source_id}/context", response_model=ContextItemPage)
def list_source_context(
    source_id: UUID,
    page: int = Query(default=1, ge=1, le=1_000_000),
    page_size: int = Query(default=25, ge=1, le=100),
    _context: AuthContext = Depends(require_roles("operator", "supervisor", "technical_admin")),
    database: OrmSession = Depends(get_db),
) -> ContextItemPage:
    if database.get(Source, source_id) is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    rows = list(
        database.scalars(
            select(ExternalContextItem)
            .where(ExternalContextItem.source_id == source_id)
            .order_by(ExternalContextItem.retrieved_at.desc(), ExternalContextItem.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
    )
    now = datetime.now(UTC)
    items = [
        ContextItemResponse(
            id=item.id,
            topic=item.topic,
            title=item.title,
            publisher=item.publisher,
            source_domain=item.source_domain,
            source_url=item.source_url,
            summary=item.summary[:1_200],
            published_at=item.published_at,
            retrieved_at=item.retrieved_at,
            freshness_status=(
                "unknown"
                if item.stale_after is None
                else "stale"
                if item.stale_after <= now
                else "current"
            ),
            processing_job_id=item.processing_job_id,
        )
        for item in rows[:page_size]
    ]
    return ContextItemPage(
        items=items, page=page, page_size=page_size, has_more=len(rows) > page_size
    )


@router.post(
    "/{source_id}/context-refresh",
    response_model=ContextRefreshAccepted,
    status_code=202,
)
def enqueue_source_context_refresh(
    source_id: UUID,
    body: ContextRefreshRequest,
    request: Request,
    context: AuthContext = Depends(require_roles("supervisor", "technical_admin")),
    _csrf: AuthContext = Depends(require_csrf),
    database: OrmSession = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> ContextRefreshAccepted:
    now = datetime.now(UTC)
    with database.begin():
        source = database.scalar(select(Source).where(Source.id == source_id).with_for_update())
        if source is None:
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        if (
            not source.context_retrieval_enabled
            or not source.context_area_label
            or source.source_type != "simulated"
        ):
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        approved_topics = source.configuration.get("context_topics", [])
        if not isinstance(approved_topics, list) or not approved_topics:
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        requested_topics = body.topics or approved_topics
        if not all(topic in approved_topics for topic in requested_topics):
            raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
        active = database.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.source_id == source.id,
                ProcessingJob.job_type == "context_enrichment",
                ProcessingJob.status.in_(("pending", "running")),
            )
            .limit(1)
        )
        if active is not None:
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        recent = database.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.source_id == source.id,
                ProcessingJob.job_type == "context_enrichment",
                ProcessingJob.created_at >= now - timedelta(minutes=10),
            )
            .limit(1)
        )
        if recent is not None:
            raise HTTPException(
                status_code=429,
                detail="Please wait before refreshing this source's public context.",
                headers={"Retry-After": "600"},
            )
        job = ProcessingJob(
            job_type="context_enrichment",
            source_id=source.id,
            created_by=context.user.id,
            status="pending",
            max_attempts=settings.worker_max_attempts,
            result_metadata={
                "topics": list(requested_topics),
                "time_window_hours": body.time_window_hours,
            },
        )
        database.add(job)
        record_security_event(
            database,
            request,
            action="source.context_refresh",
            result="success",
            actor=context.user,
            object_type="source",
            object_id=str(source.id),
        )
        database.flush()
        response = ContextRefreshAccepted(source_id=source.id, job_id=job.id, status="pending")
    return response


async def _file_chunks(path: Path) -> AsyncIterator[bytes]:
    with path.open("rb") as staged_file:
        while chunk := await asyncio.to_thread(staged_file.read, 1024 * 1024):
            yield chunk


@router.post("/upload", response_model=UploadAccepted, status_code=202)
async def upload_source(
    request: Request,
    name: str = Form(min_length=1, max_length=160),
    file: UploadFile = File(),
    context_area_label: str | None = Form(default=None, max_length=160),
    context_retrieval_enabled: bool = Form(default=False),
    context: AuthContext = Depends(require_roles("technical_admin")),
    _csrf: AuthContext = Depends(require_csrf),
    database: OrmSession = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> UploadAccepted:
    _enforce_user_limit(source_create_limiter, context.user.id)
    if context_retrieval_enabled and not context_area_label:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    if settings.storage_backend != "supabase" or not settings.supabase_configured:
        raise HTTPException(status_code=503, detail="DEPENDENCY_UNAVAILABLE")
    try:
        staged = await stage_video_upload(file, settings)
    except UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail="FILE_TOO_LARGE") from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=415, detail="UNSUPPORTED_MEDIA_TYPE") from exc
    finally:
        await file.close()

    source_id, evidence_id, job_id = uuid4(), uuid4(), uuid4()
    storage_key = (
        f"sources/{source_id}/{evidence_id}/original{Path(file.filename or '').suffix.lower()}"
    )
    storage = SupabaseStorage(settings)
    uploaded = False
    try:
        await storage.upload(
            storage_key,
            _file_chunks(staged.path),
            content_type=staged.mime_type,
            content_length=staged.byte_size,
        )
        uploaded = True
        source = Source(
            id=source_id,
            name=name.strip(),
            source_type="uploaded_clip",
            status="processing",
            context_area_label=context_area_label,
            context_retrieval_enabled=context_retrieval_enabled,
            configuration={},
            created_by=context.user.id,
        )
        evidence = Evidence(
            id=evidence_id,
            source_id=source_id,
            evidence_type="original_video",
            storage_backend="object",
            storage_key=storage_key,
            mime_type=staged.mime_type,
            byte_size=staged.byte_size,
            sha256=staged.sha256,
            status="available",
        )
        job = ProcessingJob(
            id=job_id,
            job_type="source_processing",
            source_id=source_id,
            created_by=context.user.id,
            status="pending",
            max_attempts=settings.worker_max_attempts,
            result_metadata={
                "duration_seconds": staged.duration_seconds,
                "width": staged.width,
                "height": staged.height,
                "evidence_id": str(evidence_id),
            },
        )
        database.add_all((source, evidence, job))
        record_security_event(
            database,
            request,
            action="source.upload",
            result="success",
            actor=context.user,
            object_type="source",
            object_id=str(source_id),
        )
        database.commit()
        return UploadAccepted(
            source_id=str(source_id),
            evidence_id=str(evidence_id),
            job_id=str(job_id),
            status="pending",
        )
    except Exception as exc:
        database.rollback()
        if uploaded:
            try:
                await storage.delete(storage_key)
            except StorageUnavailable:
                pass
        if isinstance(exc, StorageUnavailable):
            raise HTTPException(status_code=503, detail="DEPENDENCY_UNAVAILABLE") from exc
        raise
    finally:
        staged.remove()
        await storage.close()


@router.post("/{source_id}/process", response_model=ProcessingAccepted, status_code=202)
def request_source_processing(
    source_id: UUID,
    request: Request,
    context: AuthContext = Depends(require_roles("technical_admin")),
    _csrf: AuthContext = Depends(require_csrf),
    database: OrmSession = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> ProcessingAccepted:
    _enforce_user_limit(source_process_limiter, context.user.id)
    with database.begin():
        source = database.scalar(select(Source).where(Source.id == source_id).with_for_update())
        if source is None:
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        if source.source_type != "uploaded_clip":
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        active_job = database.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.source_id == source.id,
                ProcessingJob.job_type == "source_processing",
                ProcessingJob.status.in_(("pending", "running")),
            )
            .limit(1)
        )
        if active_job is not None:
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        evidence = database.scalar(
            select(Evidence)
            .where(Evidence.source_id == source.id, Evidence.evidence_type == "original_video")
            .order_by(Evidence.created_at.desc(), Evidence.id.desc())
            .limit(1)
        )
        if evidence is None or evidence.status != "available":
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        job = ProcessingJob(
            job_type="source_processing",
            source_id=source.id,
            created_by=context.user.id,
            status="pending",
            max_attempts=settings.worker_max_attempts,
            result_metadata={"evidence_id": str(evidence.id)},
        )
        database.add(job)
        source.status = "processing"
        record_security_event(
            database,
            request,
            action="source.process",
            result="success",
            actor=context.user,
            object_type="source",
            object_id=str(source.id),
        )
        database.flush()
        response = ProcessingAccepted(
            source_id=str(source.id), job_id=str(job.id), status="pending"
        )
    return response
