"""Incident reading and transactional human-review services."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.schemas import ReviewCreate
from app.db.models import (
    Evidence,
    Incident,
    IncidentEvidence,
    ProcessingJob,
    ReliabilityAssessment,
    Review,
    Source,
    User,
)
from app.services.audit import record_security_event


def list_incidents(
    database: OrmSession,
    *,
    start_at: datetime | None,
    end_at: datetime | None,
    source_id: UUID | None,
    detection_category: str | None,
    review_status: Literal["unreviewed", "reviewed"] | None,
    sort_by: Literal["received_at", "event_start_at", "detection_category", "review_status"],
    sort_order: Literal["asc", "desc"],
    page: int,
    page_size: int,
) -> tuple[list[tuple[Incident, ReliabilityAssessment | None]], int]:
    conditions = []
    if start_at is not None:
        conditions.append(Incident.event_start_at >= start_at)
    if end_at is not None:
        conditions.append(Incident.event_start_at <= end_at)
    if source_id is not None:
        conditions.append(Incident.source_id == source_id)
    if detection_category is not None:
        conditions.append(Incident.detection_category == detection_category)
    if review_status is not None:
        conditions.append(Incident.review_status == review_status)

    latest_assessment_id = (
        select(ReliabilityAssessment.id)
        .where(ReliabilityAssessment.incident_id == Incident.id)
        .order_by(ReliabilityAssessment.created_at.desc(), ReliabilityAssessment.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    sort_column = {
        "received_at": Incident.received_at,
        "event_start_at": Incident.event_start_at,
        "detection_category": Incident.detection_category,
        "review_status": Incident.review_status,
    }[sort_by]
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = database.execute(
        select(Incident, ReliabilityAssessment)
        .outerjoin(ReliabilityAssessment, ReliabilityAssessment.id == latest_assessment_id)
        .where(*conditions)
        .order_by(order, Incident.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size + 1)
    ).all()
    count = database.scalar(select(func.count(Incident.id)).where(*conditions)) or 0
    return [(row[0], row[1]) for row in rows[:page_size]], count


def get_incident_detail(
    database: OrmSession, incident_id: UUID, *, include_evidence: bool
) -> tuple[
    Incident,
    Source,
    list[Evidence],
    list[ReliabilityAssessment],
    list[Review],
    ProcessingJob | None,
]:
    incident = database.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    source = database.get(Source, incident.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    evidence = []
    if include_evidence:
        evidence = list(
            database.scalars(
                select(Evidence)
                .join(IncidentEvidence, IncidentEvidence.evidence_id == Evidence.id)
                .where(
                    IncidentEvidence.incident_id == incident.id,
                    Evidence.source_id == incident.source_id,
                )
                .order_by(Evidence.created_at.asc(), Evidence.id.asc())
                .limit(100)
            )
        )
    assessments = list(
        database.scalars(
            select(ReliabilityAssessment)
            .where(ReliabilityAssessment.incident_id == incident.id)
            .order_by(ReliabilityAssessment.created_at.desc(), ReliabilityAssessment.id.desc())
            .limit(50)
        )
    )
    reviews = list(
        database.scalars(
            select(Review)
            .where(Review.incident_id == incident.id)
            .order_by(Review.reviewed_at.desc(), Review.id.desc())
            .limit(50)
        )
    )
    job = (
        database.get(ProcessingJob, incident.processing_job_id)
        if incident.processing_job_id
        else None
    )
    return incident, source, evidence, assessments, reviews, job


def create_review(
    database: OrmSession,
    request: Request,
    *,
    incident_id: UUID,
    reviewer: User,
    body: ReviewCreate,
) -> Review:
    """Save the review and current review status atomically, with duplicate conflict handling."""
    with database.begin():
        incident = database.scalar(
            select(Incident).where(Incident.id == incident_id).with_for_update()
        )
        if incident is None:
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        if incident.review_status == "reviewed":
            raise HTTPException(status_code=409, detail="RESOURCE_CONFLICT")
        review = Review(
            incident_id=incident.id,
            reviewer_id=reviewer.id,
            outcome=body.outcome,
            review_note=body.review_note,
        )
        database.add(review)
        incident.review_status = "reviewed"
        record_security_event(
            database,
            request,
            action="incident.review.create",
            result="success",
            actor=reviewer,
        )
        database.flush()
    return review
