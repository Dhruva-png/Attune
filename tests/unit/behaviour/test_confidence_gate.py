from __future__ import annotations

from uuid import uuid4

from attune.behaviour.confidence import gate
from attune.core.events.schema import Event, EventType


def make_event(confidence: float) -> Event:
    return Event(
        session_id=uuid4(),
        type=EventType.YAWN,
        confidence=confidence,
        source_module="test",
    )


def test_event_at_or_above_threshold_passes_through_unchanged() -> None:
    event = make_event(0.7)
    assert gate(event, 0.6) is event


def test_event_below_threshold_is_suppressed() -> None:
    event = make_event(0.4)
    result = gate(event, 0.6)

    assert result.type == EventType.LOW_CONFIDENCE_SUPPRESSED
    assert result.session_id == event.session_id
    assert result.metadata["original_type"] == EventType.YAWN.value
    assert result.metadata["original_confidence"] == 0.4
    assert result.metadata["threshold"] == 0.6


def test_event_exactly_at_threshold_is_not_suppressed() -> None:
    event = make_event(0.6)
    assert gate(event, 0.6) is event
