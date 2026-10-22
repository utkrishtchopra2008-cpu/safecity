"""Authoritative SQLAlchemy models for the SafeCity PostgreSQL schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(Timestamped, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_normalized"),
        CheckConstraint(
            "role IN ('operator','supervisor','technical_admin')", name="ck_users_role"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_sessions_expiry_after_creation"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_sessions_token_hash_hex").ddl_if(
            dialect="postgresql"
        ),
        Index("ix_sessions_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("result IN ('success','denied','failure')", name="ck_audit_events_result"),
        Index("ix_audit_events_actor_time", "actor_user_id", "occurred_at"),
        Index("ix_audit_events_time", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100))


class Source(Timestamped, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("source_type IN ('uploaded_clip','simulated')", name="ck_sources_type"),
        CheckConstraint(
            "status IN ('ready','processing','unavailable','failed','disabled')",
            name="ck_sources_status",
        ),
        CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name="ck_sources_configuration_object"
        ),
        Index("ix_sources_status_created", "status", "created_at"),
        Index("ix_sources_creator_created", "created_by", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    context_area_label: Mapped[str | None] = mapped_column(String(160))
    context_retrieval_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_evaluation_datasets_name_version"),
        CheckConstraint(
            "status IN ('draft','ready','archived')", name="ck_evaluation_datasets_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(Text, nullable=False)
    license_identifier: Mapped[str | None] = mapped_column(String(160))
    permitted_use: Mapped[str] = mapped_column(Text, nullable=False)
    annotation_format: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProcessingJob(Timestamped, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('source_processing','evaluation','context_enrichment')",
            name="ck_jobs_type",
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="ck_jobs_status"
        ),
        CheckConstraint("attempt_count >= 0 AND max_attempts > 0", name="ck_jobs_attempts"),
        CheckConstraint("jsonb_typeof(result_metadata) = 'object'", name="ck_jobs_result_object"),
        CheckConstraint(
            "(job_type = 'evaluation' AND dataset_id IS NOT NULL AND source_id IS NULL) OR (job_type IN ('source_processing','context_enrichment') AND source_id IS NOT NULL AND dataset_id IS NULL)",
            name="ck_jobs_target_matches_type",
        ),
        CheckConstraint(
            "status <> 'completed' OR finished_at IS NOT NULL",
            name="ck_jobs_completed_has_finished_at",
        ),
        Index(
            "ix_jobs_pending_available",
            "available_at",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_jobs_status_heartbeat", "status", "heartbeat_at"),
        Index("ix_jobs_source_created", "source_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT")
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_summary: Mapped[str | None] = mapped_column(String(500))
    result_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )


class Incident(Timestamped, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "event_end_at IS NULL OR event_start_at IS NULL OR event_end_at >= event_start_at",
            name="ck_incidents_event_interval",
        ),
        CheckConstraint(
            "review_status IN ('unreviewed','reviewed')", name="ck_incidents_review_status"
        ),
        Index(
            "uq_incidents_source_event",
            "source_id",
            "source_event_id",
            unique=True,
            postgresql_where=text("source_event_id IS NOT NULL"),
        ),
        Index("ix_incidents_received", "received_at"),
        Index("ix_incidents_review_received", "review_status", "received_at"),
        Index("ix_incidents_source_event_start", "source_id", "event_start_at"),
        Index("ix_incidents_category_received", "detection_category", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    processing_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="RESTRICT")
    )
    source_event_id: Mapped[str | None] = mapped_column(String(200))
    event_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    detection_category: Mapped[str] = mapped_column(String(120), nullable=False)
    detector_name: Mapped[str] = mapped_column(String(160), nullable=False)
    detector_version: Mapped[str | None] = mapped_column(String(120))
    detector_label: Mapped[str | None] = mapped_column(String(160))
    detector_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    score_semantics: Mapped[str | None] = mapped_column(String(160))
    review_status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="unreviewed"
    )


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("storage_backend", "storage_key", name="uq_evidence_storage_key"),
        CheckConstraint(
            "evidence_type IN ('original_video','clip','frame')", name="ck_evidence_type"
        ),
        CheckConstraint("storage_backend IN ('local','object')", name="ck_evidence_backend"),
        CheckConstraint(
            "status IN ('processing','available','unavailable','failed')", name="ck_evidence_status"
        ),
        CheckConstraint("byte_size IS NULL OR byte_size >= 0", name="ck_evidence_byte_size"),
        CheckConstraint(
            "start_offset_seconds IS NULL OR start_offset_seconds >= 0",
            name="ck_evidence_start_offset",
        ),
        CheckConstraint(
            "end_offset_seconds IS NULL OR start_offset_seconds IS NULL OR end_offset_seconds >= start_offset_seconds",
            name="ck_evidence_offset_interval",
        ),
        Index("ix_evidence_source_created", "source_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(24), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(24), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(CHAR(64))
    start_offset_seconds: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    end_offset_seconds: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"
    __table_args__ = (
        CheckConstraint(
            "association_role IN ('source_context','supporting','key_frame')",
            name="ck_incident_evidence_role",
        ),
        Index("ix_incident_evidence_evidence", "evidence_id", "incident_id"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True
    )
    association_role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReliabilityAssessment(Base):
    __tablename__ = "reliability_assessments"
    __table_args__ = (
        CheckConstraint(
            "assessment_status IN ('completed','failed')", name="ck_assessments_status"
        ),
        CheckConstraint(
            "evidence_sufficiency IS NULL OR evidence_sufficiency IN ('sufficient','insufficient','unknown')",
            name="ck_assessments_sufficiency",
        ),
        CheckConstraint(
            "uncertainty_status IS NULL OR uncertainty_status IN ('not_uncertain','uncertain','abstained')",
            name="ck_assessments_uncertainty",
        ),
        CheckConstraint(
            "jsonb_typeof(measurements) = 'object'", name="ck_assessments_measurements_object"
        ),
        CheckConstraint(
            "jsonb_typeof(reason_codes) = 'array'", name="ck_assessments_reasons_array"
        ),
        CheckConstraint(
            "(assessment_status = 'completed' AND assessed_at IS NOT NULL) OR (assessment_status = 'failed' AND error_code IS NOT NULL AND evidence_sufficiency IS NULL AND uncertainty_status IS NULL)",
            name="ck_assessments_status_fields",
        ),
        Index("ix_assessments_incident_assessed", "incident_id", "assessed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    assessment_version: Mapped[str] = mapped_column(String(120), nullable=False)
    assessment_status: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence_sufficiency: Mapped[str | None] = mapped_column(String(24))
    uncertainty_status: Mapped[str | None] = mapped_column(String(24))
    measurements: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )
    reason_codes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'[]'")
    )
    error_code: Mapped[str | None] = mapped_column(String(80))
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('confirmed','false_alert','inconclusive')", name="ck_reviews_outcome"
        ),
        Index("ix_reviews_incident_reviewed", "incident_id", "reviewed_at"),
        Index("ix_reviews_reviewer_reviewed", "reviewer_id", "reviewed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    review_note: Mapped[str | None] = mapped_column(String(2000))
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvaluationAsset(Base):
    __tablename__ = "evaluation_assets"
    __table_args__ = (
        UniqueConstraint("dataset_id", "asset_key", name="uq_evaluation_assets_dataset_key"),
        CheckConstraint(
            "storage_backend IN ('local','object')", name="ck_evaluation_assets_backend"
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0", name="ck_evaluation_assets_duration"
        ),
        CheckConstraint(
            "annotation_status IN ('complete','partial','unverified')",
            name="ck_evaluation_assets_annotation_status",
        ),
        CheckConstraint(
            "availability_status IN ('available','unavailable','failed')",
            name="ck_evaluation_assets_availability_status",
        ),
        CheckConstraint(
            "jsonb_typeof(condition_labels) = 'object'",
            name="ck_evaluation_assets_conditions_object",
        ),
        CheckConstraint(
            "NOT eligible_for_metric_denominator OR (duration_seconds IS NOT NULL AND annotation_status = 'complete')",
            name="ck_evaluation_assets_eligible_complete",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    asset_key: Mapped[str] = mapped_column(String(240), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(24), nullable=False)
    media_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(CHAR(64))
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    eligible_for_metric_denominator: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    annotation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    availability_status: Mapped[str] = mapped_column(String(24), nullable=False)
    condition_labels: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )


class GroundTruthEvent(Base):
    __tablename__ = "ground_truth_events"
    __table_args__ = (
        CheckConstraint("start_offset_seconds >= 0", name="ck_ground_truth_start_nonnegative"),
        CheckConstraint(
            "end_offset_seconds > start_offset_seconds", name="ck_ground_truth_interval"
        ),
        Index("ix_ground_truth_asset_start", "dataset_asset_id", "start_offset_seconds"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_assets.id", ondelete="RESTRICT"), nullable=False
    )
    event_category: Mapped[str] = mapped_column(String(120), nullable=False)
    start_offset_seconds: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    end_offset_seconds: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    annotation_note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        UniqueConstraint("processing_job_id"),
        CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name="ck_evaluation_runs_configuration_object"
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="ck_evaluation_runs_status"
        ),
        CheckConstraint(
            "eligible_asset_count >= 0 AND excluded_asset_count >= 0 AND failed_asset_count >= 0",
            name="ck_evaluation_runs_counts",
        ),
        CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name="ck_evaluation_runs_completed_at",
        ),
        Index("ix_evaluation_runs_dataset_created", "dataset_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    processing_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    detector_name: Mapped[str] = mapped_column(String(160), nullable=False)
    detector_version: Mapped[str | None] = mapped_column(String(120))
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    eligible_asset_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    excluded_asset_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_asset_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MetricResult(Base):
    __tablename__ = "metric_results"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id", "metric_key", "scope_key", name="uq_metric_results_run_key_scope"
        ),
        CheckConstraint(
            "availability_status IN ('available','unavailable','insufficient_data')",
            name="ck_metric_results_status",
        ),
        CheckConstraint(
            "jsonb_typeof(details) = 'object'", name="ck_metric_results_details_object"
        ),
        CheckConstraint(
            "sample_count IS NULL OR sample_count >= 0", name="ck_metric_results_sample_count"
        ),
        CheckConstraint(
            "(availability_status = 'available' AND value IS NOT NULL) OR (availability_status <> 'available' AND value IS NULL)",
            name="ck_metric_results_value_availability",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="RESTRICT"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(200), nullable=False, server_default="overall")
    availability_status: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    unit: Mapped[str | None] = mapped_column(String(80))
    numerator: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    sample_count: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )
    unavailable_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalContextItem(Base):
    __tablename__ = "external_context_items"
    __table_args__ = (
        UniqueConstraint("source_id", "dedupe_key", name="uq_context_source_dedupe"),
        CheckConstraint(
            "topic IN ('weather_advisory','transport_disruption','public_notice','public_event','emergency_advisory','other')",
            name="ck_context_topic",
        ),
        CheckConstraint(
            "jsonb_typeof(provider_metadata) = 'object'", name="ck_context_metadata_object"
        ),
        Index("ix_context_source_retrieved", "source_id", "retrieved_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    processing_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(200))
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_key: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
