"""Public API schemas for incidents and human reviews."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentSummary(BaseModel):
    assessment_version: str
    assessment_status: Literal["completed", "failed"]
    evidence_sufficiency: Literal["sufficient", "insufficient", "unknown"] | None
    uncertainty_status: Literal["not_uncertain", "uncertain", "abstained"] | None
    assessed_at: datetime | None


class IncidentItem(BaseModel):
    id: UUID
    source_id: UUID
    event_start_at: datetime | None
    event_end_at: datetime | None
    received_at: datetime
    detection_category: str
    detector_name: str
    detector_version: str | None
    detector_score: Decimal | None
    score_semantics: str | None
    review_status: Literal["unreviewed", "reviewed"]
    latest_assessment: AssessmentSummary | None


class IncidentPage(BaseModel):
    items: list[IncidentItem]
    page: int
    page_size: int
    has_more: bool
    total_count: int


class SourceSummary(BaseModel):
    id: UUID
    name: str
    source_type: str
    status: str


class DetectorPrediction(BaseModel):
    category: str
    label: str | None
    detector_name: str
    detector_version: str | None
    score: Decimal | None
    score_semantics: str | None


class ReliabilityAssessment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_version: str
    assessment_status: Literal["completed", "failed"]
    evidence_sufficiency: Literal["sufficient", "insufficient", "unknown"] | None
    uncertainty_status: Literal["not_uncertain", "uncertain", "abstained"] | None
    measurements: dict[str, object]
    reason_codes: list[str]
    error_code: str | None
    assessed_at: datetime | None
    created_at: datetime


class EvidenceMetadata(BaseModel):
    id: UUID
    evidence_type: Literal["original_video", "clip", "frame"]
    mime_type: str
    byte_size: int | None
    sha256: str | None
    start_offset_seconds: Decimal | None
    end_offset_seconds: Decimal | None
    status: Literal["processing", "available", "unavailable", "failed"]


class ReviewRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    reviewer_id: UUID
    outcome: Literal["confirmed", "false_alert", "inconclusive"]
    review_note: str | None
    reviewed_at: datetime


class IncidentDetail(BaseModel):
    id: UUID
    source: SourceSummary
    processing_job_id: UUID | None
    source_event_id: str | None
    event_start_at: datetime | None
    event_end_at: datetime | None
    received_at: datetime
    detector_prediction: DetectorPrediction
    review_status: Literal["unreviewed", "reviewed"]
    evidence: list[EvidenceMetadata]
    reliability_assessments: list[ReliabilityAssessment]
    review_history: list[ReviewRecord]


class ReviewCreate(BaseModel):
    outcome: Literal["confirmed", "false_alert", "inconclusive"]
    review_note: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    review: ReviewRecord
    review_status: Literal["reviewed"]
