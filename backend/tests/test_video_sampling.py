from __future__ import annotations

import math
from uuid import uuid4

import pytest

from app.services.video_sampling import bounded_sample_frame_indices, decoder_timestamp_ms
from app.services.video_types import BoundingBox, ObjectDetection


def test_sampling_is_even_and_bounded_without_fps() -> None:
    assert bounded_sample_frame_indices(10, 4) == [0, 3, 6, 9]
    assert len(bounded_sample_frame_indices(1_000_000, 31)) == 31
    assert bounded_sample_frame_indices(3, 10) == [0, 1, 2]


@pytest.mark.parametrize("frame_count,maximum", [(0, 1), (1, 0), (-1, 5)])
def test_sampling_rejects_invalid_bounds(frame_count: int, maximum: int) -> None:
    with pytest.raises(ValueError, match="FRAME_COUNT_INVALID"):
        bounded_sample_frame_indices(frame_count, maximum)


def test_decoder_timestamps_require_finite_nonnegative_increasing_source_values() -> None:
    assert decoder_timestamp_ms(0.0, None) == 0
    assert decoder_timestamp_ms(1234.6, 1234) == 1235
    assert decoder_timestamp_ms(10.0, 10) is None
    assert decoder_timestamp_ms(9.0, 10) is None
    assert decoder_timestamp_ms(-1.0, None) is None
    assert decoder_timestamp_ms(math.nan, None) is None
    assert decoder_timestamp_ms(math.inf, None) is None


def test_detection_contract_bounds_boxes_scores_and_timestamp_state() -> None:
    base = {
        "class_name": "person",
        "score": 0.73,
        "box": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.8, "y_max": 0.9},
        "frame_index": 4,
        "timestamp_ms": 1200,
        "timestamp_status": "known",
        "detector_version": "verified-test-model",
        "evidence_id": uuid4(),
    }
    assert ObjectDetection.model_validate(base).score_semantics == "uncalibrated_model_score"
    with pytest.raises(ValueError):
        BoundingBox(x_min=0.8, y_min=0, x_max=0.2, y_max=1)
    with pytest.raises(ValueError):
        ObjectDetection.model_validate({**base, "score": 1.1})
    with pytest.raises(ValueError):
        ObjectDetection.model_validate({**base, "timestamp_status": "unknown"})
