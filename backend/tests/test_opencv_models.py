from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest

from app.services.opencv_models import (
    YOLOX_MODEL,
    YOLOX_SHA256,
    YUNET_MODEL,
    YUNET_SHA256,
    DetectorUnavailable,
    OpenCVZooModels,
    verify_model,
)


class FakeNet:
    def __init__(self, output: np.ndarray) -> None:
        self.output = output

    def setInput(self, _blob: np.ndarray) -> None:
        return None

    def getUnconnectedOutLayersNames(self) -> list[str]:
        return ["output"]

    def forward(self, _names: list[str]) -> list[np.ndarray]:
        return [self.output]


def test_model_checksum_rejects_changed_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"not a model")
    with pytest.raises(DetectorUnavailable, match="MODEL_CHECKSUM_INVALID"):
        verify_model(artifact, YOLOX_SHA256)


def test_missing_model_artifact_fails_as_unavailable(tmp_path: Path) -> None:
    with pytest.raises(DetectorUnavailable, match="MODEL_UNAVAILABLE"):
        verify_model(tmp_path / "not-downloaded.onnx", YOLOX_SHA256)


def test_object_output_is_normalized_to_observations_only() -> None:
    output = np.zeros((1, 8400, 85), dtype=np.float32)
    output[0, 0, 4] = 1.0
    output[0, 0, 5] = 0.95
    models = OpenCVZooModels(Path("unused"))
    models._object_net = FakeNet(output)  # type: ignore[assignment]
    models._face_detector = object()

    # YOLOX decoded center at (4, 4) and a positive 8x8 box on the first stride.
    output[0, 0, 2:4] = np.log(1.0)
    observations = models.detect_objects(np.zeros((240, 320, 3), dtype=np.uint8))

    assert len(observations) == 1
    assert observations[0].class_name == "person"
    assert observations[0].score == 0.95
    assert 0 <= observations[0].box.x_min < observations[0].box.x_max <= 1
    assert 0 <= observations[0].box.y_min < observations[0].box.y_max <= 1
    assert "incident" not in observations[0].class_name


def test_object_output_shape_is_checked_before_use() -> None:
    models = OpenCVZooModels(Path("unused"))
    models._object_net = FakeNet(np.zeros((1, 1, 6), dtype=np.float32))  # type: ignore[assignment]
    models._face_detector = object()
    with pytest.raises(DetectorUnavailable, match="OBJECT_OUTPUT_INVALID"):
        models.detect_objects(np.zeros((240, 320, 3), dtype=np.uint8))


def test_object_output_rejects_invalid_scores() -> None:
    output = np.zeros((1, 8400, 85), dtype=np.float32)
    output[0, 0, 4] = 1.1
    output[0, 0, 5] = 1.0
    models = OpenCVZooModels(Path("unused"))
    models._object_net = FakeNet(output)  # type: ignore[assignment]
    models._face_detector = object()
    with pytest.raises(DetectorUnavailable, match="OBJECT_OUTPUT_INVALID"):
        models.detect_objects(np.zeros((240, 320, 3), dtype=np.uint8))


class FakeFaceDetector:
    def setInputSize(self, _size: tuple[int, int]) -> None:
        return None

    def detect(self, _frame: np.ndarray) -> tuple[None, np.ndarray]:
        return None, np.ones((2, 15), dtype=np.float32)


def test_face_detector_returns_only_a_count_and_discards_regions() -> None:
    models = OpenCVZooModels(Path("unused"))
    models._object_net = object()  # type: ignore[assignment]
    models._face_detector = FakeFaceDetector()
    assert models.face_region_count(np.zeros((120, 160, 3), dtype=np.uint8)) == 2


@pytest.mark.skipif(
    not (Path("../.data/models") / YOLOX_MODEL).is_file()
    or not (Path("../.data/models") / YUNET_MODEL).is_file(),
    reason="verified local model artifacts are not configured",
)
def test_verified_models_run_on_cpu_blank_frame() -> None:
    models = OpenCVZooModels(Path("../.data/models"))
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    assert models.detect_objects(blank) == []
    assert models.face_region_count(blank) == 0
    verify_model(Path("../.data/models") / YOLOX_MODEL, YOLOX_SHA256)
    verify_model(Path("../.data/models") / YUNET_MODEL, YUNET_SHA256)


@pytest.mark.skipif(
    not (Path("../.data/models") / YOLOX_MODEL).is_file()
    or not (Path("../.data/models") / YUNET_MODEL).is_file(),
    reason="verified local model artifacts are not configured",
)
def test_verified_models_sample_video_with_bounded_metadata(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.avi"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (320, 240))
    if not writer.isOpened():
        pytest.skip("OpenCV MJPG encoder is unavailable")
    for _ in range(10):
        writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
    writer.release()

    result = OpenCVZooModels(Path("../.data/models")).sample_video(
        video_path,
        maximum_duration_seconds=900,
        deadline_monotonic=time.monotonic() + 30,
        evidence_id=uuid4(),
    )

    assert result["object_sampled_frames"] == 10
    assert result["object_taxonomy"] == "COCO-80"
    assert result["incident_detector"] == "not_implemented"
    assert result["object_observations"] == []


def test_versions_are_stable_metadata_strings() -> None:
    assert len(YOLOX_SHA256) == 64
    assert len(YUNET_SHA256) == 64
