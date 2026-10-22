from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, UploadFile

from app.core.config import AppSettings
from app.db.models import ProcessingJob, Source
from app.media.uploads import stage_video_upload
from app.worker import claim_next_job, run_once, sample_quality


def _job_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _: connection.create_function(
            "jsonb_typeof", 1, lambda value: "object" if value.startswith("{") else "array"
        ),
    )
    Source.__table__.create(engine)
    ProcessingJob.__table__.create(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def test_worker_claim_is_atomic_and_increments_attempt() -> None:
    factory, engine = _job_factory()
    job_id = uuid4()
    now = datetime.now(UTC)
    with factory() as database:
        database.add(
            ProcessingJob(
                id=job_id,
                job_type="source_processing",
                source_id=uuid4(),
                status="pending",
                attempt_count=0,
                max_attempts=3,
                available_at=now - timedelta(seconds=1),
                result_metadata={},
            )
        )
        database.commit()
    with factory() as database:
        job = claim_next_job(database, now)
        assert job is not None
        assert job.id == job_id
        assert job.status == "running"
        assert job.attempt_count == 1
    with factory() as database:
        assert claim_next_job(database, now) is None
    engine.dispose()


def test_worker_recovers_expired_lease_and_fails_exhausted_job() -> None:
    factory, engine = _job_factory()
    recoverable_id, exhausted_id = uuid4(), uuid4()
    recoverable_source, exhausted_source = uuid4(), uuid4()
    now = datetime.now(UTC)
    expired = now - timedelta(seconds=10)
    with factory() as database:
        for source_id in (recoverable_source, exhausted_source):
            database.add(
                Source(
                    id=source_id,
                    name="test source",
                    source_type="uploaded_clip",
                    status="processing",
                    configuration={},
                )
            )
        for job_id, source_id, attempts in (
            (recoverable_id, recoverable_source, 1),
            (exhausted_id, exhausted_source, 3),
        ):
            database.add(
                ProcessingJob(
                    id=job_id,
                    job_type="source_processing",
                    source_id=source_id,
                    status="running",
                    attempt_count=attempts,
                    max_attempts=3,
                    available_at=expired,
                    started_at=expired,
                    heartbeat_at=expired,
                    lease_expires_at=expired,
                    result_metadata={},
                )
            )
        database.commit()
    with factory() as database:
        claimed = claim_next_job(database, now)
        assert claimed is not None
        assert claimed.id == recoverable_id
        assert claimed.attempt_count == 2
    with factory() as database:
        exhausted = database.get(ProcessingJob, exhausted_id)
        assert exhausted is not None
        assert exhausted.status == "failed"
        assert exhausted.error_code == "JOB_LEASE_EXPIRED"
        failed_source = database.get(Source, exhausted_source)
        assert failed_source is not None
        assert failed_source.status == "failed"
    engine.dispose()


def test_quality_sampling_returns_measurements_without_event_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Capture:
        def isOpened(self) -> bool:
            return True

        def get(self, prop: int) -> float:
            if prop == cv2.CAP_PROP_FPS:
                return 1.0
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 6.0
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 32.0
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 32.0
            return 0.0

        def set(self, _prop: int, _value: float) -> bool:
            return True

        def read(self) -> tuple[bool, np.ndarray]:
            return True, np.full((32, 32, 3), 128, dtype=np.uint8)

        def release(self) -> None:
            return None

    # OpenCV construction is isolated so this test makes no model/detector claim.
    monkeypatch.setattr(cv2, "VideoCapture", lambda _path: Capture())
    fixture = tmp_path / "fixture.mp4"
    fixture.write_bytes(b"test-only")

    result = sample_quality(fixture, 60)

    assert result["sampled_frames"] == 2
    assert result["mean_luma_0_255"] == 128.0
    assert result["event_detection"] == "not_configured"


def test_real_opencv_upload_and_quality_path_on_small_generated_avi(tmp_path: Path) -> None:
    video_path = tmp_path / "fixture.avi"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (64, 64))
    assert writer.isOpened()
    for value in range(10):
        writer.write(np.full((64, 64, 3), value * 20, dtype=np.uint8))
    writer.release()

    async def validate() -> tuple[Path, float, object]:
        with video_path.open("rb") as source:
            upload = UploadFile(
                file=source,
                filename="fixture.avi",
                headers=Headers({"content-type": "video/x-msvideo"}),
            )
            staged = await stage_video_upload(upload, AppSettings(max_upload_duration_seconds=10))
            measurements = sample_quality(staged.path, 10)
            return staged.path, staged.duration_seconds, measurements

    import asyncio

    staged_path, duration, result = asyncio.run(validate())
    try:
        assert duration == 2.0
        assert result["sampled_frames"] == 1
        assert result["event_detection"] == "not_configured"
    finally:
        staged_path.unlink(missing_ok=True)


def test_worker_defaults_do_not_enable_detection() -> None:
    settings = AppSettings()

    assert settings.detector_backend == "simulated"
    assert settings.detector_version == "simulated-v1"


def test_source_context_job_fails_safely_when_provider_is_not_configured() -> None:
    import asyncio

    factory, engine = _job_factory()
    source_id, job_id = uuid4(), uuid4()
    with factory() as database:
        database.add(
            Source(
                id=source_id,
                name="Approved demo area",
                source_type="simulated",
                status="ready",
                context_area_label="Downtown",
                context_retrieval_enabled=True,
                configuration={"context_topics": ["public_notice"]},
            )
        )
        database.add(
            ProcessingJob(
                id=job_id,
                job_type="context_enrichment",
                source_id=source_id,
                status="pending",
                attempt_count=0,
                max_attempts=3,
                available_at=datetime.now(UTC) - timedelta(seconds=1),
                result_metadata={"topics": ["public_notice"], "time_window_hours": 24},
            )
        )
        database.commit()

    assert asyncio.run(run_once(factory, AppSettings())) is True
    with factory() as database:
        job = database.get(ProcessingJob, job_id)
        assert job is not None
        assert job.status == "failed"
        assert job.error_code == "CONTEXT_PROVIDER_UNAVAILABLE"
        source = database.get(Source, source_id)
        assert source is not None
        assert source.status == "ready"
    engine.dispose()
