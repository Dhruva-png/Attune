from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from attune.analytics.engine import compute_rollup
from attune.core.entities.analytics_snapshot import PeriodType
from attune.core.events.schema import Event, EventType

DAY = date(2026, 1, 5)
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


def test_empty_event_list_yields_empty_snapshot() -> None:
    snapshot = compute_rollup([], PeriodType.DAILY, DAY, DAY, SESSION_ID)

    assert snapshot.avg_focus_score is None
    assert snapshot.avg_posture_score is None
    assert snapshot.distraction_count == 0
    assert snapshot.break_count == 0
    assert snapshot.longest_break_seconds is None
    assert snapshot.best_hours == []
    assert snapshot.worst_hours == []
    assert snapshot.period_type == PeriodType.DAILY
    assert snapshot.period_start == DAY
    assert snapshot.period_end == DAY
    assert snapshot.session_id == SESSION_ID


def test_avg_focus_score_is_mean_of_focus_updates() -> None:
    events = [
        event(EventType.FOCUS_SCORE_UPDATED, 9, 0, metadata={"score": 90}),
        event(EventType.FOCUS_SCORE_UPDATED, 9, 30, metadata={"score": 85}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 0, metadata={"score": 30}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 15, metadata={"score": 35}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 30, metadata={"score": 40}),
    ]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)

    assert snapshot.avg_focus_score == 56.0
    assert snapshot.raw_metrics["focus_sample_count"] == 5


def test_distraction_count_counts_phone_pickups_only() -> None:
    events = [
        event(EventType.PHONE_PICKUP, 9, 45),
        event(EventType.PHONE_PICKUP, 14, 20),
        event(EventType.PHONE_DETECTED, 9, 44),  # visibility, not a pickup
        event(EventType.PHONE_DOWN, 9, 50),
    ]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)
    assert snapshot.distraction_count == 2


def test_break_stats_from_returned_events() -> None:
    events = [
        event(EventType.LEFT_DESK, 12, 0),
        event(EventType.RETURNED, 12, 30, duration_ms=1_800_000),
        event(EventType.LEFT_DESK, 15, 0),
        event(EventType.RETURNED, 15, 10, duration_ms=600_000),
    ]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)

    assert snapshot.break_count == 2
    assert snapshot.longest_break_seconds == 1800


def test_posture_score_is_time_weighted_across_the_day() -> None:
    events = [
        event(EventType.GOOD_POSTURE, 8, 0),
        event(EventType.POOR_POSTURE, 20, 0),
    ]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)

    # good 00:00-20:00 (20h), poor 20:00-24:00 (4h) -> 20/24 = 83.33%
    assert snapshot.avg_posture_score is not None
    assert abs(snapshot.avg_posture_score - 83.3333) < 0.01


def test_no_posture_events_yields_none_posture_score() -> None:
    events = [event(EventType.PHONE_PICKUP, 9, 0)]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)
    assert snapshot.avg_posture_score is None


def test_best_and_worst_hours_reflect_focus_buckets() -> None:
    events = [
        event(EventType.FOCUS_SCORE_UPDATED, 9, 0, metadata={"score": 90}),
        event(EventType.FOCUS_SCORE_UPDATED, 9, 30, metadata={"score": 85}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 0, metadata={"score": 30}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 15, metadata={"score": 35}),
        event(EventType.FOCUS_SCORE_UPDATED, 14, 30, metadata={"score": 40}),
    ]
    snapshot = compute_rollup(events, PeriodType.DAILY, DAY, DAY)

    assert snapshot.best_hours == ["09:00-10:00"]
    assert snapshot.worst_hours == ["14:00-15:00"]


def test_weekly_rollup_preserves_period_type_and_bounds() -> None:
    week_start = date(2026, 1, 5)
    week_end = date(2026, 1, 11)
    snapshot = compute_rollup([], PeriodType.WEEKLY, week_start, week_end)

    assert snapshot.period_type == PeriodType.WEEKLY
    assert snapshot.period_start == week_start
    assert snapshot.period_end == week_end
    assert snapshot.session_id is None
