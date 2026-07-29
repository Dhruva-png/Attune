from __future__ import annotations

from uuid import uuid4

from attune.core.events.schema import EventType
from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import BoundingBox
from attune.vision.tracking.phone_presence import PhonePresenceTracker


def box(x_min: float, y_min: float, x_max: float, y_max: float) -> BoundingBox:
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)


def test_no_detections_yields_no_event() -> None:
    tracker = PhonePresenceTracker()
    assert tracker.update([], session_id=uuid4()) is None


def test_non_phone_detections_are_ignored() -> None:
    tracker = PhonePresenceTracker()
    detections = [Detection(label="cup", confidence=0.9, bbox=box(0, 0, 10, 10))]
    assert tracker.update(detections, session_id=uuid4()) is None


def test_new_phone_track_fires_phone_detected() -> None:
    tracker = PhonePresenceTracker()
    session_id = uuid4()
    detections = [Detection(label="cell phone", confidence=0.87, bbox=box(0, 0, 10, 10))]

    event = tracker.update(detections, session_id=session_id)

    assert event is not None
    assert event.type == EventType.PHONE_DETECTED
    assert event.session_id == session_id
    assert event.confidence == 0.87
    assert event.metadata["track_id"] == 1
    assert event.metadata["bbox"] == {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10}


def test_same_phone_visible_across_frames_only_fires_once() -> None:
    tracker = PhonePresenceTracker()
    session_id = uuid4()
    detections = [Detection(label="cell phone", confidence=0.9, bbox=box(0, 0, 10, 10))]

    first = tracker.update(detections, session_id=session_id)
    second = tracker.update(detections, session_id=session_id)
    third = tracker.update(detections, session_id=session_id)

    assert first is not None
    assert second is None
    assert third is None


def test_a_second_distinct_phone_fires_its_own_event() -> None:
    tracker = PhonePresenceTracker()
    session_id = uuid4()

    first_phone = [Detection(label="cell phone", confidence=0.9, bbox=box(0, 0, 10, 10))]
    tracker.update(first_phone, session_id=session_id)

    both_phones = [
        Detection(label="cell phone", confidence=0.9, bbox=box(0, 0, 10, 10)),
        Detection(label="cell phone", confidence=0.8, bbox=box(50, 50, 60, 60)),
    ]
    event = tracker.update(both_phones, session_id=session_id)

    assert event is not None
    assert event.metadata["track_id"] == 2
