"""Bounded streaming validation for supported video uploads."""

from __future__ import annotations

import hashlib
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import AppSettings

CHUNK_SIZE = 1024 * 1024
MAX_FRAME_PIXELS = 25_000_000
SUPPORTED_MEDIA = {
    ".mp4": ("video/mp4", "mp4"),
    ".m4v": ("video/x-m4v", "mp4"),
    ".mov": ("video/quicktime", "mp4"),
    ".avi": ("video/x-msvideo", "avi"),
    ".mkv": ("video/x-matroska", "mkv"),
}


class UploadValidationError(ValueError):
    """The uploaded file is not an acceptable supported video."""


class UploadTooLarge(UploadValidationError):
    """The streamed upload exceeded the configured byte limit."""


@dataclass(frozen=True)
class StagedVideo:
    path: Path
    byte_size: int
    sha256: str
    mime_type: str
    duration_seconds: float
    width: int
    height: int

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)


def _matches_signature(header: bytes, container: str) -> bool:
    if container == "mp4":
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if container == "avi":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI "
    return header.startswith(bytes.fromhex("1a45dfa3"))


def _inspect_video(path: Path, maximum_duration: int) -> tuple[float, int, int]:
    """Open the container and decode an initial frame with bounded dimensions."""
    import cv2

    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise UploadValidationError("The video decoder could not open this file")
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
            or width * height > MAX_FRAME_PIXELS
        ):
            raise UploadValidationError("The video has invalid or unsupported stream metadata")
        duration = frame_count / fps
        if not math.isfinite(duration) or duration <= 0 or duration > maximum_duration:
            raise UploadValidationError("The video duration is invalid or exceeds the configured limit")
        decoded, frame = capture.read()
        if not decoded or frame is None:
            raise UploadValidationError("The video contains no decodable frame")
        return duration, width, height
    finally:
        capture.release()


async def stage_video_upload(file: UploadFile, settings: AppSettings) -> StagedVideo:
    """Stream to a private temporary file, enforcing limits before buffering whole content."""
    suffix = Path(file.filename or "").suffix.lower()
    media = SUPPORTED_MEDIA.get(suffix)
    if media is None or file.content_type != media[0]:
        raise UploadValidationError("Use a supported video extension and matching media type")

    descriptor, temporary_name = tempfile.mkstemp(prefix="safecity-upload-", suffix=suffix)
    path = Path(temporary_name)
    size = 0
    prefix = bytearray()
    digest = hashlib.sha256()
    try:
        with os.fdopen(descriptor, "wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise UploadTooLarge("The video exceeds the configured upload size limit")
                if len(prefix) < 32:
                    prefix.extend(chunk[: 32 - len(prefix)])
                digest.update(chunk)
                destination.write(chunk)
        if size == 0 or not _matches_signature(bytes(prefix), media[1]):
            raise UploadValidationError("The uploaded content does not match the declared video format")
        duration, width, height = _inspect_video(path, settings.max_upload_duration_seconds)
        return StagedVideo(path, size, digest.hexdigest(), media[0], duration, width, height)
    except Exception:
        path.unlink(missing_ok=True)
        raise
