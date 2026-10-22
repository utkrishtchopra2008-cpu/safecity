"""Evaluation run contracts. Creation stays unavailable until a verified detector exists."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context, require_csrf, require_roles
from app.core.rate_limit import SlidingWindowLimiter
from app.db.models import EvaluationDataset, EvaluationRun, MetricResult
from app.db.session import get_db

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
evaluation_create_limiter = SlidingWindowLimiter(limit=5, window_seconds=60)


class EvaluationMetricItem(BaseModel):
    metric_key: str
    scope_key: str
    availability_status: Literal["available", "unavailable", "insufficient_data"]
    value: Decimal | None
    unit: str | None
    numerator: Decimal | None
    denominator: Decimal | None
    sample_count: int | None
    details: dict[str, object]
    unavailable_reason: str | None


class EvaluationItem(BaseModel):
    id: UUID
    dataset_id: UUID
    dataset_name: str
    dataset_version: str
    processing_job_id: UUID
    detector_name: str
    detector_version: str | None
    configuration: dict[str, object]
    status: Literal["pending", "running", "completed", "failed"]
    eligible_asset_count: int
    excluded_asset_count: int
    failed_asset_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    metrics: list[EvaluationMetricItem]


class EvaluationPage(BaseModel):
    items: list[EvaluationItem]
    page: int
    page_size: int
    has_more: bool
    total_count: int


class EvaluationCreate(BaseModel):
    dataset_id: UUID
    detector_name: str = Field(min_length=1, max_length=160)
    detector_version: str | None = Field(default=None, max_length=120)
    configuration: dict[str, object] = Field(default_factory=dict)


class EvaluationAccepted(BaseModel):
    evaluation_id: UUID
    processing_job_id: UUID
    status: Literal["pending"]


def _to_item(database: OrmSession, run: EvaluationRun) -> EvaluationItem:
    dataset = database.get(EvaluationDataset, run.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    metrics = list(
        database.scalars(
            select(MetricResult)
            .where(MetricResult.evaluation_run_id == run.id)
            .order_by(MetricResult.metric_key.asc(), MetricResult.scope_key.asc())
        )
    )
    return EvaluationItem(
        id=run.id,
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        processing_job_id=run.processing_job_id,
        detector_name=run.detector_name,
        detector_version=run.detector_version,
        configuration=run.configuration,
        status=run.status,  # type: ignore[arg-type]
        eligible_asset_count=run.eligible_asset_count,
        excluded_asset_count=run.excluded_asset_count,
        failed_asset_count=run.failed_asset_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        metrics=[
            EvaluationMetricItem(
                metric_key=metric.metric_key,
                scope_key=metric.scope_key,
                availability_status=metric.availability_status,  # type: ignore[arg-type]
                value=metric.value,
                unit=metric.unit,
                numerator=metric.numerator,
                denominator=metric.denominator,
                sample_count=metric.sample_count,
                details=metric.details,
                unavailable_reason=metric.unavailable_reason,
            )
            for metric in metrics
        ],
    )


@router.get("", response_model=EvaluationPage)
def list_evaluations(
    page: int = Query(default=1, ge=1, le=1_000_000),
    page_size: int = Query(default=25, ge=1, le=100),
    context: AuthContext = Depends(get_auth_context),  # noqa: B008
    database: OrmSession = Depends(get_db),  # noqa: B008
) -> EvaluationPage:
    query = select(EvaluationRun).order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
    count_query = select(func.count()).select_from(EvaluationRun)
    if context.user.role == "operator":
        query = query.where(EvaluationRun.created_by == context.user.id)
        count_query = count_query.where(EvaluationRun.created_by == context.user.id)
    total = int(database.scalar(count_query) or 0)
    runs = list(database.scalars(query.offset((page - 1) * page_size).limit(page_size)))
    return EvaluationPage(
        items=[_to_item(database, run) for run in runs],
        page=page,
        page_size=page_size,
        has_more=total > page * page_size,
        total_count=total,
    )


@router.get("/{evaluation_id}", response_model=EvaluationItem)
def get_evaluation(
    evaluation_id: UUID,
    context: AuthContext = Depends(get_auth_context),  # noqa: B008
    database: OrmSession = Depends(get_db),  # noqa: B008
) -> EvaluationItem:
    run = database.get(EvaluationRun, evaluation_id)
    if run is None or (context.user.role == "operator" and run.created_by != context.user.id):
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return _to_item(database, run)


@router.post("", response_model=EvaluationAccepted, status_code=202)
def create_evaluation(
    body: EvaluationCreate,
    _request: Request,
    _context: AuthContext = Depends(require_roles("technical_admin")),  # noqa: B008
    _csrf: AuthContext = Depends(require_csrf),  # noqa: B008
    database: OrmSession = Depends(get_db),  # noqa: B008
) -> EvaluationAccepted:
    retry_after = evaluation_create_limiter.check(str(_context.user.id))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Please wait before starting another evaluation.",
            headers={"Retry-After": str(retry_after)},
        )
    dataset = database.get(EvaluationDataset, body.dataset_id)
    if dataset is None or dataset.status != "ready":
        raise HTTPException(status_code=422, detail="DATASET_UNAVAILABLE")
    # Configuration selects the worker's installed detector. This codebase has no
    # verified detector adapter/model artifact, so report the dependency honestly.
    # The worker has no verified detector adapter/model artifact; do not create a
    # run that could be mistaken for a completed or meaningful evaluation.
    raise HTTPException(status_code=503, detail="DETECTOR_UNAVAILABLE")
