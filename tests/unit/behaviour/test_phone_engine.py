from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from attune.behaviour.phone.engine import PhoneInteractionEngine, classify_interaction
from attune.core.events.schema import EventType
from attune.core.value_objects.detection import Detection, TrackedDetection
from attune.core.value_objects.geometry import BoundingBox, Landmark, Point

T0 = datetime(2026, 1, 1, 9, 0, 0)


def phone_at(x_min, y_min, x_max, y_max, track_id=1, confidence=0.9) -> TrackedDetection:
    detection = Detection(
        label="cell phone",
        confidence=confidence,
        bbox=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
    )
    return TrackedDetection(detection=detection, track_id=track_id, frames_tracked=1)


def hand_at(x, y) -> list[Landmark]:
    return [Landmark(name="wrist", point=Point(x, y, 0.0))]


def test_no_phones_yields_no_events() -> None:
    engine = PhoneInteractionEngine()
    events = engine.update([], hand_at(0.5, 0.5), uuid4(), T0)
    assert events == []


def test_phone_visible_but_hand_far_away_yields_no_pickup() -> None:
    engine = PhoneInteractionEngine()
    phone = phone_at(0.1, 0.1, 0.2, 0.2)
    events = engine.update([phone], hand_at(0.9, 0.9), uuid4(), T0)
    assert events == []


def test_hand_near_phone_triggers_pickup() -> None:
    engine = PhoneInteractionEngine()
    phone = phone_at(0.1, 0.1, 0.2, 0.2)
    events = engine.update([phone], hand_at(0.15, 0.15), uuid4(), T0)

    assert len(events) == 1
    assert events[0].type == EventType.PHONE_PICKUP
    assert events[0].metadata["track_id"] == 1


def test_pickup_only_fires_once_while_held() -> None:
    engine = PhoneInteractionEngine()
    session_id = uuid4()
    phone = phone_at(0.1, 0.1, 0.2, 0.2)
    hand = hand_at(0.15, 0.15)

    engine.update([phone], hand, session_id, T0)
    events = engine.update([phone], hand, session_id, T0 + timedelta(seconds=1))

    assert events == []


def test_release_triggers_phone_down_with_glance_classification() -> None:
    engine = PhoneInteractionEngine()
    session_id = uuid4()
    phone = phone_at(0.1, 0.1, 0.2, 0.2)

    engine.update([phone], hand_at(0.15, 0.15), session_id, T0)
    events = engine.update([phone], hand_at(0.9, 0.9), session_id, T0 + timedelta(seconds=2))

    assert len(events) == 1
    assert events[0].type == EventType.PHONE_DOWN
    assert events[0].duration_ms == 2000
    assert events[0].metadata["interaction_class"] == "glance"


def test_release_after_extended_use_classified_as_extended() -> None:
    engine = PhoneInteractionEngine()
    session_id = uuid4()
    phone = phone_at(0.1, 0.1, 0.2, 0.2)

    engine.update([phone], hand_at(0.15, 0.15), session_id, T0)
    events = engine.update([phone], hand_at(0.9, 0.9), session_id, T0 + timedelta(seconds=45))

    assert events[0].metadata["interaction_class"] == "extended"


def test_classify_interaction_boundaries() -> None:
    assert classify_interaction(1.0) == "glance"
    assert classify_interaction(3.0) == "glance"
    assert classify_interaction(3.1) == "short"
    assert classify_interaction(30.0) == "short"
    assert classify_interaction(30.1) == "extended"
