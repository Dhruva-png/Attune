from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from attune.analytics.trends import best_and_worst_hours, focus_trend, posture_trend
from attune.core.events.schema import Event, EventType

SESSION_ID = uuid4()


def event(event_type: EventType, hour: int, minute: int = 0, **kwargs) -> Event:
    return Event(
        session_id=SESSION_ID,
        type=event_type,
        timestamp=datetime(2026, 1, 5, hour, minute),
        confidence=0.9,
        source_module="test",
        **kwargs,
    )


def test_focus_trend_returns_chronological_score_points() -> None:
    events = [
        event(EventType.FOCUS_SCORE_UPDATED, 10, 0, metadata={"score": 50}),
        event(EventType.FOCUS_SCORE_UPDATED, 9, 0, metadata={"score": 80}),  # out of order input
        event(EventType.GOOD_POSTURE, 9, 30),  # ignored, not a focus event
    ]
    trend = focus_trend(events)

    assert [score for _, score in trend] == [80, 50]
    assert trend[0][0] < trend[1][0]


def test_posture_trend_maps_events_to_good_or_poor() -> None:
    events = [
        event(EventType.GOOD_POSTURE, 9, 0),
        event(EventType.POOR_POSTURE, 10, 0),
        event(EventType.PHONE_PICKUP, 9, 30),  # ignored
    ]
    trend = posture_trend(events)

    assert [state for _, state in trend] == ["good", "poor"]


def test_best_and_worst_hours_empty_when_no_focus_events() -> None:
    assert best_and_worst_hours([event(EventType.PHONE_PICKUP, 9, 0)]) == ([], [])


def test_best_and_worst_hours_with_single_bucket_has_no_worst() -> None:
    events = [event(EventType.FOCUS_SCORE_UPDATED, 9, 0, metadata={"score": 80})]
    best, worst = best_and_worst_hours(events)

    assert best == ["09:00-10:00"]
    assert worst == []


def test_best_and_worst_hours_ranks_multiple_buckets() -> None:
    events = [
        event(EventType.FOCUS_SCORE_UPDATED, 9, 0, metadata={"score": 90}),
        event(EventType.FOCUS_SCORE_UPDATED, 12, 0, metadata={"score": 60}),
        event(EventType.FOCUS_SCORE_UPDATED, 15, 0, metadata={"score": 20}),
    ]
    best, worst = best_and_worst_hours(events, top_n=1)

    assert best == ["09:00-10:00"]
    assert worst == ["15:00-16:00"]
