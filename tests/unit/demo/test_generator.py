from __future__ import annotations

import random
from datetime import date, datetime

from attune.core.entities.session import SessionStatus
from attune.core.events.schema import EventType
from attune.demo.generator import generate_session, generate_week
from attune.demo.scenarios import AVERAGE_DAY, DISTRACTED_DAY, GREAT_FOCUS_DAY

START_AT = datetime(2026, 1, 5, 9, 0)


def test_session_starts_and_ends_with_lifecycle_events() -> None:
    result = generate_session(AVERAGE_DAY, START_AT, duration_minutes=120, rng=random.Random(1))

    assert result.events[0].type == EventType.SESSION_STARTED
    assert result.events[-1].type == EventType.SESSION_ENDED
    assert result.events[0].timestamp == START_AT
    assert result.session.status == SessionStatus.COMPLETED


def test_events_are_sorted_and_within_session_bounds() -> None:
    result = generate_session(DISTRACTED_DAY, START_AT, duration_minutes=150, rng=random.Random(2))

    timestamps = [event.timestamp for event in result.events]
    assert timestamps == sorted(timestamps)
    assert all(START_AT <= ts <= result.session.ended_at for ts in timestamps)


def test_all_events_belong_to_the_generated_session() -> None:
    result = generate_session(AVERAGE_DAY, START_AT, duration_minutes=90, rng=random.Random(3))
    assert all(event.session_id == result.session.id for event in result.events)


def test_focus_scores_are_within_valid_range() -> None:
    result = generate_session(GREAT_FOCUS_DAY, START_AT, duration_minutes=120, rng=random.Random(4))
    scores = [
        event.metadata["score"]
        for event in result.events
        if event.type == EventType.FOCUS_SCORE_UPDATED
    ]
    assert scores
    assert all(0.0 <= score <= 100.0 for score in scores)


def test_session_focus_avg_matches_generated_focus_events() -> None:
    result = generate_session(AVERAGE_DAY, START_AT, duration_minutes=120, rng=random.Random(5))
    scores = [
        event.metadata["score"]
        for event in result.events
        if event.type == EventType.FOCUS_SCORE_UPDATED
    ]
    assert result.session.focus_score_avg == round(sum(scores) / len(scores), 1)


def test_session_fatigue_level_end_matches_scenario_progression() -> None:
    result = generate_session(GREAT_FOCUS_DAY, START_AT, duration_minutes=120, rng=random.Random(6))
    assert result.session.fatigue_level_end == GREAT_FOCUS_DAY.fatigue_progression[-1]


def test_phone_pickup_and_down_events_are_paired() -> None:
    result = generate_session(DISTRACTED_DAY, START_AT, duration_minutes=150, rng=random.Random(7))
    pickups = [e for e in result.events if e.type == EventType.PHONE_PICKUP]
    downs = [e for e in result.events if e.type == EventType.PHONE_DOWN]
    assert len(pickups) == len(downs)
    assert all(event.duration_ms is not None and event.duration_ms > 0 for event in downs)


def test_left_desk_and_returned_events_are_paired() -> None:
    result = generate_session(AVERAGE_DAY, START_AT, duration_minutes=150, rng=random.Random(8))
    left = [e for e in result.events if e.type == EventType.LEFT_DESK]
    returned = [e for e in result.events if e.type == EventType.RETURNED]
    assert len(left) == len(returned)
    assert all(event.duration_ms is not None and event.duration_ms > 0 for event in returned)


def test_short_session_generates_no_phone_or_break_events() -> None:
    result = generate_session(DISTRACTED_DAY, START_AT, duration_minutes=1, rng=random.Random(9))
    types = {event.type for event in result.events}
    assert EventType.PHONE_PICKUP not in types
    assert EventType.LEFT_DESK not in types


def test_generate_session_is_deterministic_given_same_seed() -> None:
    first = generate_session(AVERAGE_DAY, START_AT, duration_minutes=120, rng=random.Random(42))
    second = generate_session(AVERAGE_DAY, START_AT, duration_minutes=120, rng=random.Random(42))

    first_shape = [(e.type, e.timestamp, e.metadata) for e in first.events]
    second_shape = [(e.type, e.timestamp, e.metadata) for e in second.events]
    assert first_shape == second_shape


def test_generate_week_skips_none_days_and_uses_correct_dates() -> None:
    start = date(2026, 1, 5)  # a Monday
    week_plan = (GREAT_FOCUS_DAY, None, DISTRACTED_DAY, None, None, None, None)

    sessions = generate_week(start, week_plan=week_plan, seed=123)

    assert len(sessions) == 2
    assert sessions[0].session.started_at.date() == date(2026, 1, 5)
    assert sessions[1].session.started_at.date() == date(2026, 1, 7)


def test_generate_week_is_reproducible_with_same_seed() -> None:
    start = date(2026, 1, 5)
    first = generate_week(start, seed=99)
    second = generate_week(start, seed=99)

    assert [s.session.started_at for s in first] == [s.session.started_at for s in second]
    assert [len(s.events) for s in first] == [len(s.events) for s in second]
