"""Operational summary derived from persisted application records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context
from app.db.models import (
    EvaluationRun,
    Incident,
    MetricResult,
    ProcessingJob,
    Source,
)
from app.db.session import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class RecentIncident(BaseModel):
    id: UUID
    source_id: UUID
    received_at: datetime
    detection_category: str
    review_status: Literal["unreviewed", "reviewed"]


class DashboardSummary(BaseModel):
    period_label: str
    period_start: datetime | None
    period_end: datetime | None
    incident_counts: dict[str, int]
    recent_incidents: list[RecentIncident]
    source_counts: dict[str, int]
    job_counts: dict[str, int]
    reliability_metrics_available: bool


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    source_id: UUID | None = None,
    _context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> DashboardSummary:
    if start_at is not None and end_at is not None and start_at > end_at:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    incident_filters = []
    if start_at is not None:
        incident_filters.append(Incident.received_at >= start_at)
    if end_at is not None:
        incident_filters.append(Incident.received_at <= end_at)
    if source_id is not None:
        incident_filters.append(Incident.source_id == source_id)

    incident_counts: dict[str, int] = {"unreviewed": 0, "reviewed": 0}
    for row in database.execute(
        select(Incident.review_status, func.count())
        .where(*incident_filters)
        .group_by(Incident.review_status)
    ).all():
        incident_counts[row[0]] = row[1]

    recent_rows = database.scalars(
        select(Incident)
        .where(*incident_filters)
        .order_by(Incident.received_at.desc(), Incident.id.desc())
        .limit(10)
    )
    recent = [
        RecentIncident(
            id=item.id,
            source_id=item.source_id,
            received_at=item.received_at,
            detection_category=item.detection_category,
            review_status=cast(Literal["unreviewed", "reviewed"], item.review_status),
        )
        for item in recent_rows
    ]
    source_counts = {
        row[0]: row[1]
        for row in database.execute(
            select(Source.status, func.count()).group_by(Source.status)
        ).all()
    }
    job_counts = {
        row[0]: row[1]
        for row in database.execute(
            select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
        ).all()
    }
    reliability_available = bool(
        database.scalar(
            select(func.count(MetricResult.id))
            .join(EvaluationRun, EvaluationRun.id == MetricResult.evaluation_run_id)
            .where(
                EvaluationRun.status == "completed",
                MetricResult.availability_status == "available",
                MetricResult.value.is_not(None),
            )
        )
    )
    period_label = (
        "custom period" if start_at is not None or end_at is not None else "all available records"
    )
    return DashboardSummary(
        period_label=period_label,
        period_start=start_at,
        period_end=end_at,
        incident_counts=incident_counts,
        recent_incidents=recent,
        source_counts=source_counts,
        job_counts=job_counts,
        reliability_metrics_available=reliability_available,
    )
