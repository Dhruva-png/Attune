from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from attune.analytics.timeline import build_timeline
from attune.core.events.schema import Event, EventType

SESSION_ID = uuid4()


def event(event_type: EventType, hour: int, minute: int = 0) -> Event:
    return Event(
        session_id=SESSION_ID,
        type=event_type,
        timestamp=datetime(2026, 1, 5, hour, minute),
        confidence=0.9,
        source_module="test",
    )


def test_timeline_is_sorted_chronologically_regardless_of_input_order() -> None:
    events = [
        event(EventType.PHONE_PICKUP, 9, 18),
        event(EventType.SESSION_STARTED, 9, 0),
        event(EventType.RETURNED, 10, 31),
    ]
    timeline = build_timeline(events)

    assert [entry.label for entry in timeline] == ["Started", "Phone Pickup", "Returned"]


def test_timeline_formats_time_as_hh_mm() -> None:
    timeline = build_timeline([event(EventType.SESSION_STARTED, 9, 0)])
    assert timeline[0].time == "09:00"


def test_timeline_excludes_continuous_and_noise_events_by_default() -> None:
    events = [
        event(EventType.SESSION_STARTED, 9, 0),
        event(EventType.FOCUS_SCORE_UPDATED, 9, 5),
        event(EventType.LOW_CONFIDENCE_SUPPRESSED, 9, 10),
    ]
    timeline = build_timeline(events)

    assert [entry.event_type for entry in timeline] == [EventType.SESSION_STARTED]


def test_timeline_include_types_overrides_default_filter() -> None:
    events = [event(EventType.FOCUS_SCORE_UPDATED, 9, 5)]
    timeline = build_timeline(events, include_types=frozenset({EventType.FOCUS_SCORE_UPDATED}))

    assert len(timeline) == 1
    assert timeline[0].event_type == EventType.FOCUS_SCORE_UPDATED


def test_timeline_preserves_event_confidence() -> None:
    timeline = build_timeline([event(EventType.YAWN, 11, 0)])
    assert timeline[0].confidence == 0.9
