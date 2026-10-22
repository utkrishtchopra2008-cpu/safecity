"""Pinned OpenCV Zoo object and privacy-oriented face-region detectors.

The detectors report object classes or transient face-region counts only. They
do not classify events, identify people, track objects across frames, or retain
face boxes, crops, embeddings, or image data.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np

YOLOX_MODEL = "yolox.onnx"
YUNET_MODEL = "yunet.onnx"
YOLOX_SHA256 = "dcaae0aaa2fea4167f89235ee340eb869d3707b25712218d4c7ce921ac90e2ba"
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
YOLOX_VERSION = "opencv-zoo-yolox-s-int8bq-2022nov"
YUNET_VERSION = "opencv-zoo-yunet-2023mar"
COCO_CLASSES = (
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
)
INPUT_SIZE = 640
OBJECT_SAMPLE_INTERVAL_SECONDS = 30
MAX_OBJECT_SAMPLES = 31
MAX_OBJECTS_PER_SAMPLE = 100
MAX_AGGREGATE_CLASSES = 80
OBJECT_SCORE_THRESHOLD = 0.35
OBJECT_NMS_THRESHOLD = 0.5


class DetectorUnavailable(RuntimeError):
    """A pinned model is missing, corrupt, or cannot be initialized."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(path: Path, expected_sha256: str) -> None:
    """Fail closed when model bytes do not match the audited artifact."""
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise DetectorUnavailable("MODEL_CHECKSUM_INVALID")


class OpenCVZooModels:
    """Load models lazily and run bounded CPU-only frame inference."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        # Keep OpenCV's internal parallelism predictable in the single worker.
        cv2.setNumThreads(1)
        self._object_net: cv2.dnn.Net | None = None
        self._face_detector: Any | None = None

    def _load(self) -> None:
        if self._object_net is not None and self._face_detector is not None:
            return
        object_path = self.model_directory / YOLOX_MODEL
        face_path = self.model_directory / YUNET_MODEL
        verify_model(object_path, YOLOX_SHA256)
        verify_model(face_path, YUNET_SHA256)
        try:
            object_net = cv2.dnn.readNetFromONNX(str(object_path))
            object_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            object_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            face_detector = cv2.FaceDetectorYN.create(
                str(face_path),
                "",
                (320, 320),
                score_threshold=0.6,
                nms_threshold=0.3,
                top_k=500,
                backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                target_id=cv2.dnn.DNN_TARGET_CPU,
            )
        except cv2.error as exc:
            raise DetectorUnavailable("MODEL_INITIALIZATION_FAILED") from exc
        self._object_net = object_net
        self._face_detector = face_detector

    @staticmethod
    def _letterbox(frame: np.ndarray) -> tuple[np.ndarray, float]:
        height, width = frame.shape[:2]
        scale = min(INPUT_SIZE / height, INPUT_SIZE / width)
        resized_width = max(1, int(width * scale))
        resized_height = max(1, int(height * scale))
        resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((INPUT_SIZE, INPUT_SIZE, 3), 114, dtype=np.float32)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)
        canvas[:resized_height, :resized_width] = rgb
        return np.transpose(canvas, (2, 0, 1))[np.newaxis, ...], scale

    @staticmethod
    def _anchors() -> tuple[np.ndarray, np.ndarray]:
        grids: list[np.ndarray] = []
        strides: list[np.ndarray] = []
        for stride in (8, 16, 32):
            side = INPUT_SIZE // stride
            x_grid, y_grid = np.meshgrid(np.arange(side), np.arange(side))
            grids.append(np.stack((x_grid, y_grid), axis=2).reshape(1, -1, 2))
            strides.append(np.full((1, side * side, 1), stride, dtype=np.float32))
        return np.concatenate(grids, axis=1), np.concatenate(strides, axis=1)

    def detect_objects(self, frame: np.ndarray) -> list[tuple[str, float]]:
        self._load()
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            raise DetectorUnavailable("FRAME_INVALID")
        assert self._object_net is not None
        blob, _scale = self._letterbox(frame)
        self._object_net.setInput(blob)
        outputs = self._object_net.forward(self._object_net.getUnconnectedOutLayersNames())
        if len(outputs) != 1:
            raise DetectorUnavailable("OBJECT_OUTPUT_INVALID")
        detections = np.asarray(outputs[0], dtype=np.float32)
        if detections.ndim == 3 and detections.shape[0] == 1:
            detections = detections[0]
        expected_rows = 8400
        if detections.shape != (expected_rows, len(COCO_CLASSES) + 5):
            raise DetectorUnavailable("OBJECT_OUTPUT_INVALID")
        if not np.isfinite(detections).all():
            raise DetectorUnavailable("OBJECT_OUTPUT_INVALID")

        grids, expanded_strides = self._anchors()
        decoded = detections.copy()
        decoded[:, :2] = (decoded[:, :2] + grids[0]) * expanded_strides[0]
        with np.errstate(over="ignore", invalid="ignore"):
            decoded[:, 2:4] = np.exp(decoded[:, 2:4]) * expanded_strides[0]
        if not np.isfinite(decoded[:, :4]).all():
            raise DetectorUnavailable("OBJECT_OUTPUT_INVALID")
        scores = decoded[:, 4:5] * decoded[:, 5:]
        class_ids = np.argmax(scores, axis=1)
        confidence = np.max(scores, axis=1)
        eligible = np.flatnonzero(confidence >= OBJECT_SCORE_THRESHOLD)
        if len(eligible) == 0:
            return []
        boxes = decoded[eligible, :4]
        xywh = np.column_stack(
            (boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2, boxes[:, 2], boxes[:, 3])
        )
        keep = cv2.dnn.NMSBoxesBatched(
            xywh.tolist(),
            confidence[eligible].tolist(),
            class_ids[eligible].tolist(),
            OBJECT_SCORE_THRESHOLD,
            OBJECT_NMS_THRESHOLD,
        )
        kept_indices = np.asarray(keep).reshape(-1)[:MAX_OBJECTS_PER_SAMPLE]
        return [
            (
                COCO_CLASSES[int(class_ids[eligible[index]])],
                round(float(confidence[eligible[index]]), 4),
            )
            for index in kept_indices
        ]

    def face_region_count(self, frame: np.ndarray) -> int:
        """Return only a count; discard all face boxes immediately."""
        self._load()
        height, width = frame.shape[:2]
        if width < 1 or height < 1:
            raise DetectorUnavailable("FRAME_INVALID")
        assert self._face_detector is not None
        self._face_detector.setInputSize((width, height))
        try:
            _status, faces = self._face_detector.detect(frame)
        except cv2.error as exc:
            raise DetectorUnavailable("FACE_OUTPUT_INVALID") from exc
        return 0 if faces is None else min(len(faces), 500)

    def sample_video(
        self,
        video_path: Path,
        *,
        maximum_duration_seconds: int,
        deadline_monotonic: float,
    ) -> dict[str, object]:
        """Sample object classes and transient face regions without storing images/boxes."""
        self._load()
        capture = cv2.VideoCapture(str(video_path))
        try:
            if not capture.isOpened():
                raise DetectorUnavailable("VIDEO_DECODER_UNAVAILABLE")
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if (
                not math.isfinite(fps)
                or not math.isfinite(frame_count)
                or fps <= 0
                or frame_count <= 0
            ):
                raise DetectorUnavailable("VIDEO_METADATA_INVALID")
            duration = frame_count / fps
            if not math.isfinite(duration) or duration <= 0 or duration > maximum_duration_seconds:
                raise DetectorUnavailable("VIDEO_DURATION_INVALID")
            last_offset = min(
                int(duration), (MAX_OBJECT_SAMPLES - 1) * OBJECT_SAMPLE_INTERVAL_SECONDS
            )
            counts: Counter[str] = Counter()
            confidence_sums: dict[str, float] = {}
            confidence_counts: Counter[str] = Counter()
            face_frames = 0
            face_regions = 0
            sampled = 0
            for second in range(0, last_offset + 1, OBJECT_SAMPLE_INTERVAL_SECONDS):
                if time.monotonic() >= deadline_monotonic:
                    raise TimeoutError("VIDEO_DETECTOR_TIMEOUT")
                capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
                decoded, frame = capture.read()
                if not decoded or frame is None:
                    continue
                objects = self.detect_objects(frame)
                if time.monotonic() >= deadline_monotonic:
                    raise TimeoutError("VIDEO_DETECTOR_TIMEOUT")
                face_count = self.face_region_count(frame)
                if time.monotonic() >= deadline_monotonic:
                    raise TimeoutError("VIDEO_DETECTOR_TIMEOUT")
                sampled += 1
                if face_count:
                    face_frames += 1
                    face_regions += face_count
                for label, confidence in objects:
                    counts[label] += 1
                    confidence_sums[label] = confidence_sums.get(label, 0.0) + confidence
                    confidence_counts[label] += 1
            observations = [
                {
                    "class_name": label,
                    "sample_count": counts[label],
                    "mean_score": round(confidence_sums[label] / confidence_counts[label], 4),
                }
                for label in sorted(counts)[:MAX_AGGREGATE_CLASSES]
            ]
            return {
                "object_detector": YOLOX_VERSION,
                "object_model_sha256": YOLOX_SHA256,
                "object_taxonomy": "COCO-80",
                "object_sample_interval_seconds": OBJECT_SAMPLE_INTERVAL_SECONDS,
                "object_sampled_frames": sampled,
                "object_observations": observations,
                "face_region_detector": YUNET_VERSION,
                "face_model_sha256": YUNET_SHA256,
                "face_region_sampled_frames": sampled,
                "face_region_frames_with_faces": face_frames,
                "face_region_count": face_regions,
                "incident_detector": "not_implemented",
            }
        finally:
            capture.release()
