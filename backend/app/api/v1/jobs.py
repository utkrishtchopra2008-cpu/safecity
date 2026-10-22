"""Authorized processing-job and system-status reads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context
from app.db.models import ProcessingJob, Source
from app.db.session import get_db

router = APIRouter(tags=["jobs", "system"])


class JobStatus(BaseModel):
    id: UUID
    job_type: Literal["source_processing", "evaluation", "context_enrichment"]
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    error_code: str | None
    error_summary: str | None
    result_metadata: dict[str, object]


class SystemStatus(BaseModel):
    status: Literal["available", "degraded"]
    sources: dict[str, int]
    jobs: dict[str, int]


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(
    job_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> JobStatus:
    job = database.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    owns_job = job.created_by == context.user.id
    if not owns_job and context.user.role != "technical_admin":
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    can_read_diagnostics = context.user.role == "technical_admin"
    safe_result_keys = {
        "duration_seconds",
        "width",
        "height",
        "evidence_id",
        "result_count",
        "eligible_asset_count",
        "excluded_asset_count",
    }
    result_metadata: dict[str, object] = (
        {
            key: value
            for key, value in job.result_metadata.items()
            if key in safe_result_keys and isinstance(value, (str, int, float, bool))
        }
        if can_read_diagnostics
        else {}
    )
    return JobStatus(
        id=job.id,
        job_type=cast(
            Literal["source_processing", "evaluation", "context_enrichment"], job.job_type
        ),
        status=cast(Literal["pending", "running", "completed", "failed"], job.status),
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        attempt_count=job.attempt_count,
        error_code=job.error_code if can_read_diagnostics else None,
        error_summary=job.error_summary if can_read_diagnostics else None,
        result_metadata=result_metadata,
    )


@router.get("/system/status", response_model=SystemStatus)
def system_status(
    context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> SystemStatus:
    if context.user.role not in {"supervisor", "technical_admin"}:
        return SystemStatus(status="available", sources={}, jobs={})
    source_counts: dict[str, int] = {
        row[0]: row[1]
        for row in database.execute(
            select(Source.status, func.count()).group_by(Source.status)
        ).all()
    }
    job_counts: dict[str, int] = {
        row[0]: row[1]
        for row in database.execute(
            select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
        ).all()
    }
    degraded = bool(job_counts.get("failed", 0)) or bool(source_counts.get("failed", 0))
    return SystemStatus(
        status="degraded" if degraded else "available",
        sources=source_counts,
        jobs=job_counts,
    )
