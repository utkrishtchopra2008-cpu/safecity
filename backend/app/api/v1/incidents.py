"""Typed incident listing, detail, and human-review routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, get_auth_context, require_csrf, require_roles
from app.api.v1.schemas import (
    AssessmentSummary,
    DetectorPrediction,
    EvidenceMetadata,
    IncidentDetail,
    IncidentItem,
    IncidentPage,
    ReliabilityAssessment,
    ReviewCreate,
    ReviewRecord,
    ReviewResponse,
    SourceSummary,
)
from app.db.session import get_db
from app.services.incidents import create_review, get_incident_detail, list_incidents

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentPage)
def list_incident_route(
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    source_id: UUID | None = None,
    detection_category: str | None = Query(default=None, min_length=1, max_length=120),
    review_status: Literal["unreviewed", "reviewed"] | None = None,
    sort_by: Literal[
        "received_at", "event_start_at", "detection_category", "review_status"
    ] = "received_at",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1, le=1_000_000),
    page_size: int = Query(default=25, ge=1, le=100),
    _context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> IncidentPage:
    if start_at is not None and end_at is not None and start_at > end_at:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    rows, total_count = list_incidents(
        database,
        start_at=start_at,
        end_at=end_at,
        source_id=source_id,
        detection_category=detection_category,
        review_status=review_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    items = [
        IncidentItem(
            id=incident.id,
            source_id=incident.source_id,
            event_start_at=incident.event_start_at,
            event_end_at=incident.event_end_at,
            received_at=incident.received_at,
            detection_category=incident.detection_category,
            detector_name=incident.detector_name,
            detector_version=incident.detector_version,
            detector_score=incident.detector_score,
            score_semantics=incident.score_semantics,
            review_status=cast(Literal["unreviewed", "reviewed"], incident.review_status),
            latest_assessment=(
                AssessmentSummary.model_validate(assessment, from_attributes=True)
                if assessment is not None
                else None
            ),
        )
        for incident, assessment in rows
    ]
    return IncidentPage(
        items=items,
        page=page,
        page_size=page_size,
        has_more=total_count > page * page_size,
        total_count=total_count,
    )


@router.get("/{incident_id}", response_model=IncidentDetail)
def incident_detail_route(
    incident_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> IncidentDetail:
    include_evidence = context.user.role in {"operator", "supervisor"}
    incident, source, evidence, assessments, reviews, _job = get_incident_detail(
        database, incident_id, include_evidence=include_evidence
    )
    return IncidentDetail(
        id=incident.id,
        source=SourceSummary(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            status=source.status,
        ),
        processing_job_id=incident.processing_job_id,
        source_event_id=incident.source_event_id,
        event_start_at=incident.event_start_at,
        event_end_at=incident.event_end_at,
        received_at=incident.received_at,
        detector_prediction=DetectorPrediction(
            category=incident.detection_category,
            label=incident.detector_label,
            detector_name=incident.detector_name,
            detector_version=incident.detector_version,
            score=incident.detector_score,
            score_semantics=incident.score_semantics,
        ),
        review_status=cast(Literal["unreviewed", "reviewed"], incident.review_status),
        evidence=[
            EvidenceMetadata(
                id=item.id,
                evidence_type=cast(Literal["original_video", "clip", "frame"], item.evidence_type),
                mime_type=item.mime_type,
                byte_size=item.byte_size,
                sha256=item.sha256,
                start_offset_seconds=item.start_offset_seconds,
                end_offset_seconds=item.end_offset_seconds,
                status=cast(
                    Literal["processing", "available", "unavailable", "failed"], item.status
                ),
            )
            for item in evidence
        ],
        reliability_assessments=[
            ReliabilityAssessment.model_validate(item, from_attributes=True) for item in assessments
        ],
        review_history=[
            ReviewRecord.model_validate(item, from_attributes=True) for item in reviews
        ],
    )


@router.post("/{incident_id}/reviews", response_model=ReviewResponse)
def submit_review_route(
    incident_id: UUID,
    body: ReviewCreate,
    request: Request,
    context: AuthContext = Depends(require_roles("operator", "supervisor")),
    _csrf: AuthContext = Depends(require_csrf),
    database: OrmSession = Depends(get_db),
) -> ReviewResponse:
    review = create_review(
        database,
        request,
        incident_id=incident_id,
        reviewer=context.user,
        body=body,
    )
    return ReviewResponse(
        review=ReviewRecord.model_validate(review, from_attributes=True), review_status="reviewed"
    )


@router.get("/{incident_id}/reviews", response_model=list[ReviewRecord])
def list_review_route(
    incident_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    database: OrmSession = Depends(get_db),
) -> list[ReviewRecord]:
    _incident, _source, _evidence, _assessments, reviews, _job = get_incident_detail(
        database,
        incident_id,
        include_evidence=context.user.role in {"operator", "supervisor"},
    )
    return [ReviewRecord.model_validate(item, from_attributes=True) for item in reviews]
