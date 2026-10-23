"""Bounded source-frame selection and decoder-timestamp validation."""

from __future__ import annotations

import math


def bounded_sample_frame_indices(frame_count: int, maximum_samples: int) -> list[int]:
    """Choose evenly spaced frame indices without deriving source times from FPS."""
    if frame_count < 1 or maximum_samples < 1:
        raise ValueError("FRAME_COUNT_INVALID")
    sample_count = min(frame_count, maximum_samples)
    if sample_count == 1:
        return [0]
    return [round(index * (frame_count - 1) / (sample_count - 1)) for index in range(sample_count)]


def decoder_timestamp_ms(position_milliseconds: float, previous_ms: int | None) -> int | None:
    """Accept finite, nonnegative, strictly increasing decoder source timestamps only."""
    if not math.isfinite(position_milliseconds) or position_milliseconds < 0:
        return None
    timestamp = round(position_milliseconds)
    if previous_ms is not None and timestamp <= previous_ms:
        return None
    return timestamp
