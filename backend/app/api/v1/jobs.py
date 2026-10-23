"""Authorized processing-job and system-status reads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context
from app.db.models import ProcessingJob, Source
from app.db.session import get_db
from app.services.video_types import ObjectDetection, QualityMeasurement

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
    can_read_results = owns_job or can_read_diagnostics
    safe_result_keys = {
        "duration_seconds",
        "width",
        "height",
        "sampled_frames",
        "sample_interval_seconds",
        "mean_luma_0_255",
        "mean_laplacian_variance",
        "quality_observation_version",
        "quality_measurements",
        "quality_result_status",
        "quality_uncertainty_reasons",
        "source_timestamp_availability",
        "requested_sample_frames",
        "evidence_id",
        "result_count",
        "eligible_asset_count",
        "excluded_asset_count",
        "object_detector",
        "object_model_sha256",
        "object_taxonomy",
        "object_sample_interval_seconds",
        "object_sampled_frames",
        "object_observations",
        "object_detections",
        "object_detection_limit_reached",
        "object_timestamp_status",
        "object_decode_failures",
        "face_region_detector",
        "face_model_sha256",
        "face_region_sampled_frames",
        "face_region_frames_with_faces",
        "face_region_count",
        "incident_detector",
    }
    result_metadata: dict[str, object] = {}
    if can_read_results:
        for key, value in job.result_metadata.items():
            if key not in safe_result_keys:
                continue
            if isinstance(value, (str, int, float, bool)):
                result_metadata[key] = value
            elif key == "object_observations" and isinstance(value, list):
                safe_observations = [
                    {
                        "class_name": observation["class_name"],
                        "sample_count": observation["sample_count"],
                        "mean_score": observation["mean_score"],
                    }
                    for observation in value[:80]
                    if isinstance(observation, dict)
                    and isinstance(observation.get("class_name"), str)
                    and isinstance(observation.get("sample_count"), int)
                    and isinstance(observation.get("mean_score"), (int, float))
                ]
                result_metadata[key] = safe_observations
            elif key == "object_detections" and isinstance(value, list):
                safe_detections: list[dict[str, object]] = []
                for detection in value[:500]:
                    if not isinstance(detection, dict):
                        continue
                    try:
                        safe_detections.append(
                            ObjectDetection.model_validate(detection).model_dump(mode="json")
                        )
                    except ValidationError:
                        continue
                result_metadata[key] = safe_detections
            elif key == "quality_measurements" and isinstance(value, list):
                safe_measurements: list[dict[str, object]] = []
                for measurement in value[:32]:
                    if not isinstance(measurement, dict):
                        continue
                    try:
                        safe_measurements.append(
                            QualityMeasurement.model_validate(measurement).model_dump(mode="json")
                        )
                    except ValidationError:
                        continue
                result_metadata[key] = safe_measurements
            elif key == "quality_uncertainty_reasons" and isinstance(value, list):
                result_metadata[key] = [
                    reason[:80] for reason in value[:20] if isinstance(reason, str)
                ]
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
