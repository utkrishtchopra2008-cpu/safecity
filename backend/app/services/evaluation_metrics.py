"""Deterministic metrics for already-normalized evaluation events.

Matching rule v1: category must match exactly and time intervals must overlap
with positive duration. Matching is one-to-one and maximizes match count; ties
prefer greater overlap, earlier predictions and stable input order. Unmatched
predictions count as false alerts (including repeated detections); unmatched
ground-truth events count as misses. This deliberately conservative rule is
versioned in each evaluation configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Event:
    category: str
    start_seconds: Decimal
    end_seconds: Decimal


@dataclass(frozen=True)
class Metric:
    key: str
    status: Literal["available", "unavailable", "insufficient_data"]
    value: Decimal | None
    unit: str
    numerator: Decimal | None
    denominator: Decimal | None
    sample_count: int | None
    reason: str | None = None


def _ratio(
    key: str,
    numerator: int,
    denominator: int,
    *,
    unit: str = "ratio",
    sample_count: int | None = None,
) -> Metric:
    if denominator == 0:
        return Metric(
            key,
            "unavailable",
            None,
            unit,
            Decimal(numerator),
            Decimal(denominator),
            sample_count,
            "The metric denominator is zero.",
        )
    return Metric(
        key,
        "available",
        Decimal(numerator) / Decimal(denominator),
        unit,
        Decimal(numerator),
        Decimal(denominator),
        sample_count,
    )


def calculate_metrics(
    predictions: list[Event],
    ground_truth: list[Event],
    *,
    eligible_video_seconds: Decimal,
    eligible_asset_count: int | None = None,
    review_durations_seconds: list[Decimal] | None = None,
    minimum_sample_count: int = 1,
) -> tuple[list[Metric], dict[str, int | str]]:
    """Calculate event metrics without treating absent or undefined data as zero."""
    if eligible_video_seconds < 0 or minimum_sample_count < 1:
        raise ValueError("evaluation_input_invalid")
    if len(predictions) + len(ground_truth) > 1000:
        raise ValueError("evaluation_event_limit_exceeded")
    if any(
        event.start_seconds < 0 or event.end_seconds <= event.start_seconds
        for event in predictions + ground_truth
    ):
        raise ValueError("evaluation_event_interval_invalid")

    candidates: dict[int, list[int]] = {}
    overlaps: dict[tuple[int, int], Decimal] = {}
    for pi, prediction in enumerate(predictions):
        for gi, truth in enumerate(ground_truth):
            overlap = min(prediction.end_seconds, truth.end_seconds) - max(
                prediction.start_seconds, truth.start_seconds
            )
            if prediction.category == truth.category and overlap > 0:
                candidates.setdefault(pi, []).append(gi)
                overlaps[(pi, gi)] = overlap
    for pi, matches in candidates.items():
        matches.sort(key=lambda gi: (-overlaps[(pi, gi)], ground_truth[gi].start_seconds, gi))

    # Hopcroft-Karp gives a maximum-cardinality one-to-one event matching.
    paired_prediction: dict[int, int] = {}
    paired_truth: dict[int, int] = {}
    distance: dict[int, int] = {}

    def build_layers() -> bool:
        queue: list[int] = []
        for pi in range(len(predictions)):
            if pi not in paired_prediction:
                distance[pi] = 0
                queue.append(pi)
            else:
                distance[pi] = -1
        found_free_truth = False
        cursor = 0
        while cursor < len(queue):
            pi = queue[cursor]
            cursor += 1
            for gi in candidates.get(pi, []):
                next_pi = paired_truth.get(gi)
                if next_pi is None:
                    found_free_truth = True
                elif distance[next_pi] < 0:
                    distance[next_pi] = distance[pi] + 1
                    queue.append(next_pi)
        return found_free_truth

    def augment(pi: int) -> bool:
        for gi in candidates.get(pi, []):
            next_pi = paired_truth.get(gi)
            if next_pi is None or (distance.get(next_pi) == distance[pi] + 1 and augment(next_pi)):
                paired_prediction[pi] = gi
                paired_truth[gi] = pi
                return True
        distance[pi] = -1
        return False

    while build_layers():
        for pi in range(len(predictions)):
            if pi not in paired_prediction:
                augment(pi)
    delays: list[Decimal] = []
    for pi, gi in paired_prediction.items():
        delays.append(
            max(Decimal(0), predictions[pi].start_seconds - ground_truth[gi].start_seconds)
        )

    tp = len(paired_prediction)
    fp = len(predictions) - tp
    fn = len(ground_truth) - len(paired_truth)
    metrics = [
        _ratio("precision", tp, tp + fp, sample_count=tp + fp),
        _ratio("recall", tp, tp + fn, sample_count=tp + fn),
    ]
    if eligible_video_seconds == 0:
        metrics.append(
            Metric(
                "false_alerts_per_hour",
                "unavailable",
                None,
                "alerts per eligible video hour",
                Decimal(fp),
                Decimal(0),
                0,
                "No eligible monitored-video duration is available.",
            )
        )
    else:
        hours = eligible_video_seconds / Decimal(3600)
        metrics.append(
            Metric(
                "false_alerts_per_hour",
                "available",
                Decimal(fp) / hours,
                "alerts per eligible video hour",
                Decimal(fp),
                hours,
                eligible_asset_count,
            )
        )
    if len(delays) < minimum_sample_count:
        metrics.append(
            Metric(
                "detection_delay",
                "insufficient_data",
                None,
                "seconds",
                Decimal(sum(delays, Decimal(0))) if delays else None,
                Decimal(len(delays)) if delays else None,
                len(delays),
                "Too few matched events to report detection delay.",
            )
        )
    else:
        metrics.append(
            Metric(
                "detection_delay",
                "available",
                sum(delays, Decimal(0)) / Decimal(len(delays)),
                "seconds",
                sum(delays, Decimal(0)),
                Decimal(len(delays)),
                len(delays),
            )
        )
    durations = review_durations_seconds or []
    if any(duration < 0 for duration in durations):
        raise ValueError("review_duration_invalid")
    if not durations:
        metrics.append(
            Metric(
                "review_time",
                "unavailable",
                None,
                "seconds",
                None,
                None,
                0,
                "Reliable review-duration measurements are not available.",
            )
        )
    else:
        total_duration = sum(durations, Decimal(0))
        metrics.append(
            Metric(
                "review_time",
                "available",
                total_duration / Decimal(len(durations)),
                "seconds",
                total_duration,
                Decimal(len(durations)),
                len(durations),
            )
        )
    return metrics, {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "matching_rule": "exact_category_positive_interval_overlap_one_to_one_v1",
    }
