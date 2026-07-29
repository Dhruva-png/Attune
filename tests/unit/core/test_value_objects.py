from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from attune.core.value_objects import BoundingBox, Confidence, TimeRange


def test_confidence_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        Confidence(1.1)
    with pytest.raises(ValueError):
        Confidence(-0.01)


@pytest.mark.parametrize(
    ("value", "threshold", "expected"),
    [(0.9, 0.6, True), (0.6, 0.6, True), (0.5, 0.6, False)],
)
def test_confidence_is_reliable_gating(value: float, threshold: float, expected: bool) -> None:
    assert Confidence(value).is_reliable(threshold) is expected


def test_bounding_box_rejects_inverted_coordinates() -> None:
    with pytest.raises(ValueError):
        BoundingBox(x_min=10, y_min=0, x_max=0, y_max=10)


def test_bounding_box_derived_properties() -> None:
    box = BoundingBox(x_min=0, y_min=0, x_max=10, y_max=20)
    assert box.width == 10
    assert box.height == 20
    assert box.center.x == 5
    assert box.center.y == 10


def test_time_range_rejects_end_before_start() -> None:
    now = datetime.utcnow()
    with pytest.raises(ValueError):
        TimeRange(start=now, end=now - timedelta(seconds=1))


def test_time_range_duration_and_contains() -> None:
    start = datetime(2026, 1, 1, 9, 0, 0)
    end = start + timedelta(minutes=5)
    time_range = TimeRange(start=start, end=end)

    assert time_range.duration_seconds == 300
    assert time_range.contains(start + timedelta(minutes=2))
    assert not time_range.contains(end + timedelta(seconds=1))
