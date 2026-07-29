from __future__ import annotations

from uuid import uuid4

import pytest
from attune.core.events.schema import Event, EventType
from pydantic import ValidationError


def test_event_confidence_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        Event(session_id=uuid4(), type=EventType.YAWN, confidence=1.5, source_module="test")


def test_event_confidence_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        Event(session_id=uuid4(), type=EventType.YAWN, confidence=-0.1, source_module="test")


def test_event_is_immutable() -> None:
    event = Event(session_id=uuid4(), type=EventType.YAWN, confidence=0.8, source_module="test")
    with pytest.raises(ValidationError):
        event.confidence = 0.1  # type: ignore[misc]


def test_event_defaults_id_timestamp_and_metadata() -> None:
    event = Event(
        session_id=uuid4(), type=EventType.COFFEE_DRINK, confidence=0.7, source_module="test"
    )
    assert event.id is not None
    assert event.timestamp is not None
    assert event.metadata == {}
    assert event.duration_ms is None
