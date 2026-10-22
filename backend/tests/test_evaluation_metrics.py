from decimal import Decimal as D

import pytest

from app.services.evaluation_metrics import Event, calculate_metrics


def metric_map(metrics):
    return {metric.key: metric for metric in metrics}


def test_hand_calculated_metrics_use_one_to_one_exact_category_overlap():
    predictions = [
        Event("fall", D("10"), D("15")),
        Event("fall", D("12"), D("16")),  # repeated detection remains an FP
        Event("wrong-class", D("40"), D("43")),
    ]
    truth = [Event("fall", D("11"), D("14")), Event("theft", D("50"), D("52"))]
    metrics, counts = calculate_metrics(
        predictions,
        truth,
        eligible_video_seconds=D("7200"),
        eligible_asset_count=2,
        review_durations_seconds=[D("30"), D("50")],
    )
    values = metric_map(metrics)

    assert counts["true_positive"] == 1
    assert counts["false_positive"] == 2
    assert counts["false_negative"] == 1
    assert counts["matching_rule"] == "exact_category_positive_interval_overlap_one_to_one_v1"
    assert values["precision"].value == D("1") / D("3")
    assert values["recall"].value == D("0.5")
    assert values["false_alerts_per_hour"].value == D("1")
    assert values["false_alerts_per_hour"].denominator == D("2")
    assert values["false_alerts_per_hour"].sample_count == 2
    assert values["detection_delay"].value == D("0")
    assert values["review_time"].value == D("40")


def test_undefined_denominators_and_absent_review_time_are_not_zero():
    metrics, _ = calculate_metrics(
        [], [], eligible_video_seconds=D("0"), review_durations_seconds=[]
    )
    values = metric_map(metrics)
    assert values["precision"].status == "unavailable"
    assert values["precision"].value is None
    assert values["recall"].status == "unavailable"
    assert values["false_alerts_per_hour"].status == "unavailable"
    assert values["detection_delay"].status == "insufficient_data"
    assert values["review_time"].status == "unavailable"
    assert all(
        metric.value is None
        for metric in metrics
        if metric.status in {"unavailable", "insufficient_data"}
    )


def test_detection_delay_can_require_minimum_sample_count():
    metrics, _ = calculate_metrics(
        [Event("fall", D("5"), D("8"))],
        [Event("fall", D("3"), D("6"))],
        eligible_video_seconds=D("3600"),
        minimum_sample_count=2,
    )
    delay = metric_map(metrics)["detection_delay"]
    assert delay.status == "insufficient_data"
    assert delay.value is None
    assert delay.sample_count == 1


def test_matching_maximizes_true_positives_before_applying_overlap_preference():
    metrics, counts = calculate_metrics(
        [Event("fall", D("5"), D("15")), Event("fall", D("0"), D("6"))],
        [Event("fall", D("0"), D("10")), Event("fall", D("10"), D("20"))],
        eligible_video_seconds=D("3600"),
    )
    assert counts["true_positive"] == 2
    assert metric_map(metrics)["precision"].value == D("1")


@pytest.mark.parametrize(
    ("predictions", "truth", "seconds", "reviews"),
    [
        ([Event("fall", D("0"), D("0"))], [], D("1"), None),
        ([], [Event("fall", D("-1"), D("1"))], D("1"), None),
        ([], [], D("-1"), None),
        ([], [], D("1"), [D("-1")]),
    ],
)
def test_invalid_intervals_durations_and_denominators_are_rejected(
    predictions, truth, seconds, reviews
):
    with pytest.raises(ValueError):
        calculate_metrics(
            predictions,
            truth,
            eligible_video_seconds=seconds,
            review_durations_seconds=reviews,
        )
