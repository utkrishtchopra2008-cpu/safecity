"""Download the pinned OpenCV Zoo models into private local model storage."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.opencv_models import (
    YOLOX_MODEL,
    YOLOX_SHA256,
    YUNET_MODEL,
    YUNET_SHA256,
)

MODEL_ARTIFACTS = (
    (
        YOLOX_MODEL,
        "https://huggingface.co/opencv/object_detection_yolox/resolve/"
        "78c368f74ce73ee28fc7a1be418a598c71b58b52/object_detection_yolox_2022nov_int8bq.onnx",
        YOLOX_SHA256,
        12_000_000,
    ),
    (
        YUNET_MODEL,
        "https://huggingface.co/opencv/face_detection_yunet/resolve/"
        "3cc26e7f1014a5ee5d74a42acee58bafc9d0a310/face_detection_yunet_2023mar.onnx",
        YUNET_SHA256,
        500_000,
    ),
)
LICENSE_ARTIFACTS = (
    (
        "YOLOX-LICENSE.txt",
        "https://huggingface.co/opencv/object_detection_yolox/resolve/"
        "78c368f74ce73ee28fc7a1be418a598c71b58b52/LICENSE",
        "0ec3668d3274bcf29e8a29e9576d5a2cd96fc78d3c5bec4387355a796e5d9088",
        50_000,
    ),
    (
        "YuNet-LICENSE.txt",
        "https://huggingface.co/opencv/face_detection_yunet/resolve/"
        "3cc26e7f1014a5ee5d74a42acee58bafc9d0a310/LICENSE",
        "c83b8120c50ccbd4c4f96edf53141bdd566ebb8f8e9227e415326aa1b1aba958",
        50_000,
    ),
)


def download_model(
    directory: Path, filename: str, url: str, expected_sha256: str, max_bytes: int
) -> None:
    """Stream one pinned model and atomically install only verified bytes."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = directory / filename
    if destination.is_file():
        if _sha256(destination) == expected_sha256:
            return
        raise ValueError(f"Existing model checksum mismatch: {filename}")

    digest = hashlib.sha256()
    size = 0
    temporary_path: Path | None = None
    try:
        with httpx.stream(
            "GET", url, timeout=httpx.Timeout(30.0), follow_redirects=True
        ) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length is not None and int(content_length) > max_bytes:
                raise ValueError(f"Model exceeds the configured download cap: {filename}")
            with tempfile.NamedTemporaryFile(
                dir=directory, prefix=".model-", delete=False
            ) as output:
                temporary_path = Path(output.name)
                for chunk in response.iter_bytes(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError(f"Model exceeds the configured download cap: {filename}")
                    digest.update(chunk)
                    output.write(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError(f"Downloaded model checksum mismatch: {filename}")
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    model_directory = get_settings().detector_model_dir
    for filename, url, expected_sha256, max_bytes in MODEL_ARTIFACTS:
        download_model(model_directory, filename, url, expected_sha256, max_bytes)
        print(f"Verified {filename} in {model_directory}")
    for filename, url, expected_sha256, max_bytes in LICENSE_ARTIFACTS:
        download_model(model_directory, filename, url, expected_sha256, max_bytes)
        print(f"Verified {filename} in {model_directory}")


if __name__ == "__main__":
    main()
