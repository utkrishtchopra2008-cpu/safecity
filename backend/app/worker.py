"""Single PostgreSQL-backed worker for bounded video quality and observations.

Optional pinned object/face-region models report coarse observations only. The worker
never classifies events or creates incidents from model outputs.
"""

from __future__ import annotations

import asyncio
import logging
import math
import tempfile
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import cv2
from sqlalchemy import select, update
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from app.core.config import AppSettings, get_settings
from app.db.models import Evidence, ProcessingJob, Source
from app.db.session import get_engine
from app.services.context_jobs import process_context_job
from app.services.opencv_models import DetectorUnavailable, OpenCVZooModels
from app.storage.supabase import StorageUnavailable, SupabaseStorage

logger = logging.getLogger("safecity.worker")
CLAIM_LEASE_SECONDS = 180
MAX_SAMPLES = 181
SAMPLE_INTERVAL_SECONDS = 5
MAX_JOB_SECONDS = 120


@lru_cache(maxsize=1)
def _get_opencv_models(model_directory: Path) -> OpenCVZooModels:
    return OpenCVZooModels(model_directory)


def claim_next_job(database: OrmSession, now: datetime | None = None) -> ProcessingJob | None:
    """Atomically claim one available job; release expired leases within a short transaction."""
    current = now or datetime.now(UTC)
    with database.begin():
        retry_ids = list(
            database.scalars(
                select(ProcessingJob.id)
                .where(
                    ProcessingJob.status == "running",
                    ProcessingJob.lease_expires_at.is_not(None),
                    ProcessingJob.lease_expires_at <= current,
                    ProcessingJob.attempt_count < ProcessingJob.max_attempts,
                )
                .order_by(ProcessingJob.lease_expires_at.asc())
                .limit(100)
            )
        )
        terminal_rows = database.execute(
            select(ProcessingJob.id, ProcessingJob.source_id)
            .where(
                ProcessingJob.status == "running",
                ProcessingJob.lease_expires_at.is_not(None),
                ProcessingJob.lease_expires_at <= current,
                ProcessingJob.attempt_count >= ProcessingJob.max_attempts,
            )
            .order_by(ProcessingJob.lease_expires_at.asc())
            .limit(100)
        ).all()
        database.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id.in_(retry_ids))
            .values(status="pending", started_at=None, heartbeat_at=None, lease_expires_at=None)
        )
        database.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id.in_([row[0] for row in terminal_rows]))
            .values(
                status="failed",
                finished_at=current,
                error_code="JOB_LEASE_EXPIRED",
                error_summary="Processing did not finish within its execution lease.",
            )
        )
        expired_source_ids = [row[1] for row in terminal_rows if row[1] is not None]
        if expired_source_ids:
            database.execute(
                update(Source).where(Source.id.in_(expired_source_ids)).values(status="failed")
            )
        job = database.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.status == "pending", ProcessingJob.available_at <= current)
            .order_by(ProcessingJob.available_at.asc(), ProcessingJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.attempt_count += 1
        job.started_at = current
        job.heartbeat_at = current
        job.lease_expires_at = current + timedelta(seconds=CLAIM_LEASE_SECONDS)
        job.error_code = None
        job.error_summary = None
        database.flush()
        return job


def sample_quality(
    path: Path,
    maximum_duration_seconds: int,
    *,
    deadline_monotonic: float | None = None,
) -> dict[str, Any]:
    """Measure coarse video quality on bounded samples without retaining any frames."""
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError("VIDEO_DECODER_UNAVAILABLE")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if (
            not math.isfinite(fps)
            or not math.isfinite(frame_count)
            or fps <= 0
            or frame_count <= 0
            or width <= 0
            or height <= 0
            or width * height > 25_000_000
        ):
            raise ValueError("VIDEO_METADATA_INVALID")
        duration = frame_count / fps
        if not math.isfinite(duration) or duration <= 0 or duration > maximum_duration_seconds:
            raise ValueError("VIDEO_DURATION_INVALID")
        brightness: list[float] = []
        sharpness: list[float] = []
        started = time.monotonic()
        last_offset = min(int(duration), (MAX_SAMPLES - 1) * SAMPLE_INTERVAL_SECONDS)
        for second in range(0, last_offset + 1, SAMPLE_INTERVAL_SECONDS):
            if time.monotonic() - started > MAX_JOB_SECONDS or (
                deadline_monotonic is not None and time.monotonic() >= deadline_monotonic
            ):
                raise TimeoutError("VIDEO_QUALITY_TIMEOUT")
            capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            decoded, frame = capture.read()
            if not decoded or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness.append(float(gray.mean()))
            sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        if not brightness:
            raise ValueError("VIDEO_NO_SAMPLED_FRAMES")
        return {
            "quality_observation_version": "opencv-quality-v1",
            "duration_seconds": round(duration, 3),
            "width": width,
            "height": height,
            "sampled_frames": len(brightness),
            "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "mean_luma_0_255": round(sum(brightness) / len(brightness), 3),
            "mean_laplacian_variance": round(sum(sharpness) / len(sharpness), 3),
            "event_detection": "not_configured",
        }
    finally:
        capture.release()


def _finish_failure(
    factory: sessionmaker[OrmSession], job_id: UUID, code: str, summary: str, *, retryable: bool
) -> None:
    now = datetime.now(UTC)
    with factory() as database, database.begin():
        job = database.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
        )
        if job is None or job.status != "running":
            return
        can_retry = retryable and job.attempt_count < job.max_attempts
        job.status = "pending" if can_retry else "failed"
        job.error_code = code
        job.error_summary = summary[:500]
        job.finished_at = None if can_retry else now
        job.available_at = now + timedelta(seconds=min(60, 2**job.attempt_count))
        job.lease_expires_at = None
        job.heartbeat_at = now
        if not can_retry and job.source_id is not None:
            source = database.get(Source, job.source_id)
            if source is not None and job.job_type == "source_processing":
                source.status = "failed"


def _finish_success(
    factory: sessionmaker[OrmSession], job_id: UUID, source_id: UUID, measurements: dict[str, Any]
) -> None:
    now = datetime.now(UTC)
    with factory() as database, database.begin():
        job = database.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
        )
        if job is None or job.status != "running":
            return
        job.status = "completed"
        job.finished_at = now
        job.heartbeat_at = now
        job.lease_expires_at = None
        job.result_metadata = {**job.result_metadata, **measurements}
        source = database.get(Source, source_id)
        if source is not None:
            source.status = "ready"
            source.last_processed_at = now


async def run_once(factory: sessionmaker[OrmSession], settings: AppSettings) -> bool:
    with factory() as database:
        claimed = claim_next_job(database)
        if claimed is None:
            return False
        job_id = claimed.id
        job_type = claimed.job_type
        source_id = claimed.source_id
        evidence_id_value = claimed.result_metadata.get("evidence_id")

    if job_type == "context_enrichment" and source_id is not None:
        try:
            await process_context_job(factory, settings, job_id, source_id)
        except ValueError as exc:
            _finish_failure(
                factory,
                job_id,
                str(exc) if str(exc).startswith("CONTEXT_") else "CONTEXT_PROCESSING_FAILED",
                "Public context refresh could not be completed.",
                retryable=False,
            )
        return True
    if job_type != "source_processing" or source_id is None:
        _finish_failure(
            factory,
            job_id,
            "PROCESSOR_UNAVAILABLE",
            "No verified handler is configured for this job type.",
            retryable=False,
        )
        return True
    if settings.storage_backend != "supabase" or not settings.supabase_configured:
        _finish_failure(
            factory,
            job_id,
            "STORAGE_UNAVAILABLE",
            "Private storage is not configured for processing.",
            retryable=True,
        )
        return True
    try:
        evidence_id = UUID(str(evidence_id_value))
    except (ValueError, TypeError):
        _finish_failure(
            factory,
            job_id,
            "EVIDENCE_REFERENCE_INVALID",
            "The queued job has no valid evidence reference.",
            retryable=False,
        )
        return True

    with factory() as database:
        evidence = database.get(Evidence, evidence_id)
        if evidence is None or evidence.source_id != source_id:
            _finish_failure(
                factory,
                job_id,
                "EVIDENCE_REFERENCE_INVALID",
                "The queued job evidence is unavailable.",
                retryable=False,
            )
            return True
        storage_key = evidence.storage_key

    storage = SupabaseStorage(settings)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="safecity-worker-", delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
        temporary_path.unlink(missing_ok=True)
        byte_size = await storage.download_to_path(
            storage_key, temporary_path, maximum_bytes=settings.max_upload_bytes
        )
        deadline = time.monotonic() + MAX_JOB_SECONDS
        measurements = sample_quality(
            temporary_path,
            settings.max_upload_duration_seconds,
            deadline_monotonic=deadline,
        )
        if settings.detector_backend == "opencv_zoo":
            measurements.update(
                _get_opencv_models(settings.detector_model_dir).sample_video(
                    temporary_path,
                    maximum_duration_seconds=settings.max_upload_duration_seconds,
                    deadline_monotonic=deadline,
                )
            )
        measurements["downloaded_bytes"] = byte_size
        _finish_success(factory, job_id, source_id, measurements)
    except TimeoutError:
        _finish_failure(
            factory,
            job_id,
            "VIDEO_PROCESSING_TIMEOUT",
            "Bounded video processing exceeded its time limit.",
            retryable=False,
        )
    except ValueError as exc:
        code = str(exc) if str(exc).startswith("VIDEO_") else "VIDEO_PROCESSING_FAILED"
        _finish_failure(
            factory,
            job_id,
            code,
            "The uploaded video could not be sampled safely.",
            retryable=False,
        )
    except DetectorUnavailable as exc:
        _finish_failure(
            factory,
            job_id,
            str(exc)
            if str(exc).startswith(("MODEL_", "OBJECT_", "FACE_", "FRAME_", "VIDEO_"))
            else "MODEL_UNAVAILABLE",
            "The configured detector could not produce a validated result.",
            retryable=False,
        )
    except cv2.error:
        _finish_failure(
            factory,
            job_id,
            "VIDEO_DECODER_FAILED",
            "The configured decoder could not sample this video.",
            retryable=False,
        )
    except StorageUnavailable as exc:
        _finish_failure(
            factory,
            job_id,
            "STORAGE_UNAVAILABLE",
            "Private evidence could not be retrieved for processing.",
            retryable=exc.retryable,
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await storage.close()
    return True


async def serve() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    logger.info("worker_started detector_backend=%s", settings.detector_backend)
    while True:
        try:
            found_job = await run_once(factory, settings)
        except Exception:
            logger.exception("worker_cycle_failed category=internal")
            found_job = False
        if not found_job:
            await asyncio.sleep(settings.worker_poll_interval_seconds)


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
