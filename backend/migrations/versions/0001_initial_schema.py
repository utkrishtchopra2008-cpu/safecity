"""Create the SafeCity persistence schema.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE users (
        id UUID PRIMARY KEY, email VARCHAR(320) NOT NULL UNIQUE,
        display_name VARCHAR(120) NOT NULL, password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(32) NOT NULL CHECK (role IN ('operator','supervisor','technical_admin')),
        is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_users_email_normalized CHECK (email = lower(email)))""")
    op.execute("""CREATE TABLE sessions (
        id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        token_hash CHAR(64) NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL, last_seen_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ,
        CONSTRAINT ck_sessions_expiry_after_creation CHECK (expires_at > created_at),
        CONSTRAINT ck_sessions_token_hash_hex CHECK (token_hash ~ '^[0-9a-f]{64}$'))""")
    op.execute("CREATE INDEX ix_sessions_user_expires ON sessions(user_id, expires_at)")
    op.execute("""CREATE TABLE audit_events (
        id UUID PRIMARY KEY, actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        actor_role VARCHAR(32) NOT NULL, action VARCHAR(80) NOT NULL,
        object_type VARCHAR(80) NOT NULL, object_id VARCHAR(200),
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        result VARCHAR(24) NOT NULL CHECK (result IN ('success','denied','failure')),
        correlation_id VARCHAR(100))""")
    op.execute(
        "CREATE INDEX ix_audit_events_actor_time ON audit_events(actor_user_id, occurred_at)"
    )
    op.execute("CREATE INDEX ix_audit_events_time ON audit_events(occurred_at)")
    op.execute("""CREATE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit events are append-only'; END;
        $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW
        EXECUTE FUNCTION reject_audit_event_mutation()""")
    op.execute("""CREATE TABLE sources (
        id UUID PRIMARY KEY, name VARCHAR(160) NOT NULL,
        source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('uploaded_clip','simulated')),
        status VARCHAR(32) NOT NULL CHECK (status IN ('ready','processing','unavailable','failed','disabled')),
        context_area_label VARCHAR(160), context_retrieval_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        configuration JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(configuration) = 'object'),
        created_by UUID REFERENCES users(id) ON DELETE SET NULL, last_processed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_sources_status_created ON sources(status, created_at)")
    op.execute("CREATE INDEX ix_sources_creator_created ON sources(created_by, created_at)")
    op.execute("""CREATE TABLE evaluation_datasets (
        id UUID PRIMARY KEY, name VARCHAR(160) NOT NULL, version VARCHAR(80) NOT NULL,
        description TEXT, provenance TEXT NOT NULL, license_identifier VARCHAR(160),
        permitted_use TEXT NOT NULL, annotation_format VARCHAR(80) NOT NULL,
        status VARCHAR(24) NOT NULL CHECK (status IN ('draft','ready','archived')),
        created_by UUID REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_evaluation_datasets_name_version UNIQUE(name, version))""")
    op.execute("""CREATE TABLE processing_jobs (
        id UUID PRIMARY KEY,
        job_type VARCHAR(32) NOT NULL CHECK (job_type IN ('source_processing','evaluation','context_enrichment')),
        status VARCHAR(24) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
        source_id UUID REFERENCES sources(id) ON DELETE RESTRICT,
        dataset_id UUID REFERENCES evaluation_datasets(id) ON DELETE RESTRICT,
        created_by UUID REFERENCES users(id) ON DELETE SET NULL,
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
        max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
        available_at TIMESTAMPTZ NOT NULL DEFAULT now(), started_at TIMESTAMPTZ,
        heartbeat_at TIMESTAMPTZ, lease_expires_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
        error_code VARCHAR(80), error_summary VARCHAR(500),
        result_metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(result_metadata) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_jobs_target_matches_type CHECK (
          (job_type = 'evaluation' AND dataset_id IS NOT NULL AND source_id IS NULL) OR
          (job_type IN ('source_processing','context_enrichment') AND source_id IS NOT NULL AND dataset_id IS NULL)),
        CONSTRAINT ck_jobs_completed_has_finished_at CHECK (status <> 'completed' OR finished_at IS NOT NULL))""")
    op.execute(
        "CREATE INDEX ix_jobs_pending_available ON processing_jobs(available_at, created_at) WHERE status = 'pending'"
    )
    op.execute("CREATE INDEX ix_jobs_status_heartbeat ON processing_jobs(status, heartbeat_at)")
    op.execute("CREATE INDEX ix_jobs_source_created ON processing_jobs(source_id, created_at)")
    op.execute("""CREATE TABLE incidents (
        id UUID PRIMARY KEY, source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
        processing_job_id UUID REFERENCES processing_jobs(id) ON DELETE RESTRICT,
        source_event_id VARCHAR(200), event_start_at TIMESTAMPTZ, event_end_at TIMESTAMPTZ,
        received_at TIMESTAMPTZ NOT NULL DEFAULT now(), detection_category VARCHAR(120) NOT NULL,
        detector_name VARCHAR(160) NOT NULL, detector_version VARCHAR(120), detector_label VARCHAR(160),
        detector_score NUMERIC(20,10), score_semantics VARCHAR(160),
        review_status VARCHAR(24) NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','reviewed')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_incidents_event_interval CHECK (event_end_at IS NULL OR event_start_at IS NULL OR event_end_at >= event_start_at))""")
    op.execute(
        "CREATE UNIQUE INDEX uq_incidents_source_event ON incidents(source_id, source_event_id) WHERE source_event_id IS NOT NULL"
    )
    op.execute("CREATE INDEX ix_incidents_received ON incidents(received_at)")
    op.execute("CREATE INDEX ix_incidents_review_received ON incidents(review_status, received_at)")
    op.execute(
        "CREATE INDEX ix_incidents_source_event_start ON incidents(source_id, event_start_at)"
    )
    op.execute(
        "CREATE INDEX ix_incidents_category_received ON incidents(detection_category, received_at)"
    )
    op.execute("""CREATE TABLE evidence (
        id UUID PRIMARY KEY, source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
        evidence_type VARCHAR(24) NOT NULL CHECK (evidence_type IN ('original_video','clip','frame')),
        storage_backend VARCHAR(24) NOT NULL CHECK (storage_backend IN ('local','object')),
        storage_key TEXT NOT NULL, mime_type VARCHAR(120) NOT NULL, byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
        sha256 CHAR(64), start_offset_seconds NUMERIC(14,3), end_offset_seconds NUMERIC(14,3),
        status VARCHAR(24) NOT NULL CHECK (status IN ('processing','available','unavailable','failed')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_evidence_storage_key UNIQUE(storage_backend, storage_key),
        CONSTRAINT ck_evidence_start_offset CHECK (start_offset_seconds IS NULL OR start_offset_seconds >= 0),
        CONSTRAINT ck_evidence_offset_interval CHECK (end_offset_seconds IS NULL OR start_offset_seconds IS NULL OR end_offset_seconds >= start_offset_seconds))""")
    op.execute("CREATE INDEX ix_evidence_source_created ON evidence(source_id, created_at)")
    op.execute("""CREATE TABLE incident_evidence (
        incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
        evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE RESTRICT,
        association_role VARCHAR(24) NOT NULL CHECK (association_role IN ('source_context','supporting','key_frame')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(incident_id, evidence_id))""")
    op.execute(
        "CREATE INDEX ix_incident_evidence_evidence ON incident_evidence(evidence_id, incident_id)"
    )
    op.execute("""CREATE TABLE reliability_assessments (
        id UUID PRIMARY KEY, incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
        assessment_version VARCHAR(120) NOT NULL,
        assessment_status VARCHAR(24) NOT NULL CHECK (assessment_status IN ('completed','failed')),
        evidence_sufficiency VARCHAR(24) CHECK (evidence_sufficiency IN ('sufficient','insufficient','unknown')),
        uncertainty_status VARCHAR(24) CHECK (uncertainty_status IN ('not_uncertain','uncertain','abstained')),
        measurements JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(measurements) = 'object'),
        reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(reason_codes) = 'array'),
        error_code VARCHAR(80), assessed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_assessments_status_fields CHECK (
          (assessment_status = 'completed' AND assessed_at IS NOT NULL) OR
          (assessment_status = 'failed' AND error_code IS NOT NULL AND evidence_sufficiency IS NULL AND uncertainty_status IS NULL)))""")
    op.execute(
        "CREATE INDEX ix_assessments_incident_assessed ON reliability_assessments(incident_id, assessed_at)"
    )
    op.execute("""CREATE TABLE reviews (
        id UUID PRIMARY KEY, incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
        reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        outcome VARCHAR(32) NOT NULL CHECK (outcome IN ('confirmed','false_alert','inconclusive')),
        review_note VARCHAR(2000), reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_reviews_incident_reviewed ON reviews(incident_id, reviewed_at)")
    op.execute("CREATE INDEX ix_reviews_reviewer_reviewed ON reviews(reviewer_id, reviewed_at)")
    op.execute("""CREATE TABLE evaluation_assets (
        id UUID PRIMARY KEY, dataset_id UUID NOT NULL REFERENCES evaluation_datasets(id) ON DELETE RESTRICT,
        asset_key VARCHAR(240) NOT NULL, storage_backend VARCHAR(24) NOT NULL CHECK (storage_backend IN ('local','object')),
        media_storage_key TEXT NOT NULL, sha256 CHAR(64), duration_seconds NUMERIC(14,3),
        eligible_for_metric_denominator BOOLEAN NOT NULL DEFAULT FALSE,
        annotation_status VARCHAR(24) NOT NULL CHECK (annotation_status IN ('complete','partial','unverified')),
        availability_status VARCHAR(24) NOT NULL CHECK (availability_status IN ('available','unavailable','failed')),
        condition_labels JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(condition_labels) = 'object'),
        CONSTRAINT uq_evaluation_assets_dataset_key UNIQUE(dataset_id, asset_key),
        CONSTRAINT ck_evaluation_assets_duration CHECK (duration_seconds IS NULL OR duration_seconds > 0),
        CONSTRAINT ck_evaluation_assets_eligible_complete CHECK (NOT eligible_for_metric_denominator OR (duration_seconds IS NOT NULL AND annotation_status = 'complete')))""")
    op.execute("""CREATE TABLE ground_truth_events (
        id UUID PRIMARY KEY, dataset_asset_id UUID NOT NULL REFERENCES evaluation_assets(id) ON DELETE RESTRICT,
        event_category VARCHAR(120) NOT NULL, start_offset_seconds NUMERIC(14,3) NOT NULL,
        end_offset_seconds NUMERIC(14,3) NOT NULL, annotation_note VARCHAR(1000), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_ground_truth_start_nonnegative CHECK (start_offset_seconds >= 0),
        CONSTRAINT ck_ground_truth_interval CHECK (end_offset_seconds > start_offset_seconds))""")
    op.execute(
        "CREATE INDEX ix_ground_truth_asset_start ON ground_truth_events(dataset_asset_id, start_offset_seconds)"
    )
    op.execute("""CREATE TABLE evaluation_runs (
        id UUID PRIMARY KEY, dataset_id UUID NOT NULL REFERENCES evaluation_datasets(id) ON DELETE RESTRICT,
        processing_job_id UUID NOT NULL UNIQUE REFERENCES processing_jobs(id) ON DELETE RESTRICT,
        detector_name VARCHAR(160) NOT NULL, detector_version VARCHAR(120),
        configuration JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(configuration) = 'object'),
        status VARCHAR(24) NOT NULL CHECK (status IN ('pending','running','completed','failed')),
        eligible_asset_count INTEGER NOT NULL DEFAULT 0, excluded_asset_count INTEGER NOT NULL DEFAULT 0,
        failed_asset_count INTEGER NOT NULL DEFAULT 0, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_evaluation_runs_counts CHECK (eligible_asset_count >= 0 AND excluded_asset_count >= 0 AND failed_asset_count >= 0),
        CONSTRAINT ck_evaluation_runs_completed_at CHECK (status <> 'completed' OR completed_at IS NOT NULL))""")
    op.execute(
        "CREATE INDEX ix_evaluation_runs_dataset_created ON evaluation_runs(dataset_id, created_at)"
    )
    op.execute("""CREATE TABLE metric_results (
        id UUID PRIMARY KEY, evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs(id) ON DELETE RESTRICT,
        metric_key VARCHAR(80) NOT NULL, scope_key VARCHAR(200) NOT NULL DEFAULT 'overall',
        availability_status VARCHAR(24) NOT NULL CHECK (availability_status IN ('available','unavailable','insufficient_data')),
        value NUMERIC(24,10), unit VARCHAR(80), numerator NUMERIC(24,10), denominator NUMERIC(24,10),
        sample_count INTEGER CHECK (sample_count IS NULL OR sample_count >= 0),
        details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object'),
        unavailable_reason VARCHAR(500), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_metric_results_run_key_scope UNIQUE(evaluation_run_id, metric_key, scope_key),
        CONSTRAINT ck_metric_results_value_availability CHECK (
          (availability_status = 'available' AND value IS NOT NULL) OR
          (availability_status <> 'available' AND value IS NULL)))""")
    op.execute("""CREATE TABLE external_context_items (
        id UUID PRIMARY KEY, source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
        processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
        topic VARCHAR(80) NOT NULL CHECK (topic IN ('weather_advisory','transport_disruption','public_notice','public_event','emergency_advisory','other')),
        title VARCHAR(400) NOT NULL, publisher VARCHAR(200), source_domain VARCHAR(255) NOT NULL,
        source_url TEXT NOT NULL, summary TEXT NOT NULL, published_at TIMESTAMPTZ,
        retrieved_at TIMESTAMPTZ NOT NULL, stale_after TIMESTAMPTZ, dedupe_key CHAR(64) NOT NULL,
        provider_metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(provider_metadata) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_context_source_dedupe UNIQUE(source_id, dedupe_key))""")
    op.execute(
        "CREATE INDEX ix_context_source_retrieved ON external_context_items(source_id, retrieved_at)"
    )


def downgrade() -> None:
    for table in (
        "external_context_items",
        "metric_results",
        "evaluation_runs",
        "ground_truth_events",
        "evaluation_assets",
        "reviews",
        "reliability_assessments",
        "incident_evidence",
        "evidence",
        "incidents",
        "processing_jobs",
        "evaluation_datasets",
        "sources",
        "audit_events",
        "sessions",
        "users",
    ):
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION reject_audit_event_mutation()")
