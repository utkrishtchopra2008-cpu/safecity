"""Reliability summaries sourced only from persisted labeled evaluations."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context
from app.db.models import EvaluationDataset, EvaluationRun, MetricResult
from app.db.session import get_db

router = APIRouter(prefix="/reliability", tags=["reliability"])

METRIC_UNITS = {
    "false_alerts_per_hour": "alerts per eligible video hour",
    "precision": "ratio",
    "recall": "ratio",
    "detection_delay": "seconds",
    "review_time": "seconds",
}


class ReliabilityMetric(BaseModel):
    metric_key: str
    value: Decimal | None
    unit: str | None
    availability_status: Literal["available", "unavailable", "insufficient_data"]
    sample_count: int | None
    numerator: Decimal | None
    denominator: Decimal | None
    scope_key: str
    unavailable_reason: str | None
    evaluation_id: UUID | None
    dataset_name: str | None
    dataset_version: str | None
    data_source: Literal["labeled_evaluation"]


class ReliabilityResponse(BaseModel):
    metrics: list[ReliabilityMetric]
    provenance: str


@router.get("/summary", response_model=ReliabilityResponse)
def reliability_summary(
    evaluation_id: UUID | None = None,
    context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> ReliabilityResponse:
    query = (
        select(MetricResult, EvaluationRun, EvaluationDataset)
        .join(EvaluationRun, EvaluationRun.id == MetricResult.evaluation_run_id)
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationRun.dataset_id)
        .where(EvaluationRun.status == "completed")
        .order_by(EvaluationRun.created_at.desc(), MetricResult.metric_key.asc())
        .limit(500)
    )
    if evaluation_id is not None:
        query = query.where(EvaluationRun.id == evaluation_id)
        selected_run = database.get(EvaluationRun, evaluation_id)
        if selected_run is None or (
            context.user.role == "operator" and selected_run.created_by != context.user.id
        ):
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    elif context.user.role == "operator":
        query = query.where(EvaluationRun.created_by == context.user.id)
    rows = database.execute(query).all()
    metrics: list[ReliabilityMetric] = []
    represented: set[str] = set()
    for result, run, dataset in rows:
        if result.metric_key not in METRIC_UNITS:
            continue
        represented.add(result.metric_key)
        available = result.availability_status == "available" and result.value is not None
        metrics.append(
            ReliabilityMetric(
                metric_key=result.metric_key,
                value=result.value if available else None,
                unit=result.unit or METRIC_UNITS[result.metric_key],
                availability_status=result.availability_status,
                sample_count=result.sample_count,
                numerator=result.numerator,
                denominator=result.denominator,
                scope_key=result.scope_key,
                unavailable_reason=result.unavailable_reason,
                evaluation_id=run.id,
                dataset_name=dataset.name,
                dataset_version=dataset.version,
                data_source="labeled_evaluation",
            )
        )
    if not rows:
        represented.clear()
    for metric_key, unit in METRIC_UNITS.items():
        if metric_key not in represented:
            metrics.append(
                ReliabilityMetric(
                    metric_key=metric_key,
                    value=None,
                    unit=unit,
                    availability_status="unavailable",
                    sample_count=None,
                    numerator=None,
                    denominator=None,
                    scope_key="overall",
                    unavailable_reason="No supported labeled evaluation result is recorded.",
                    evaluation_id=evaluation_id,
                    dataset_name=None,
                    dataset_version=None,
                    data_source="labeled_evaluation",
                )
            )
    return ReliabilityResponse(
        metrics=metrics,
        provenance=(
            "Metrics are read from completed, labeled evaluation runs. Operational reviews and public context are not substituted."
        ),
    )
