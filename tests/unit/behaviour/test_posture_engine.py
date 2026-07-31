from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from attune.behaviour.posture.engine import PostureAnalyzer
from attune.core.events.schema import EventType
from attune.core.value_objects.geometry import Landmark, Point

T0 = datetime(2026, 1, 1, 9, 0, 0)


def landmark(name: str, x: float, y: float, visibility: float = 1.0) -> Landmark:
    return Landmark(name=name, point=Point(x, y, 0.0), visibility=visibility)


def good_posture_landmarks(visibility: float = 1.0) -> list[Landmark]:
    return [
        landmark("nose", 0.5, 0.2, visibility),
        landmark("left_shoulder", 0.4, 0.4, visibility),
        landmark("right_shoulder", 0.6, 0.4, visibility),
        landmark("left_hip", 0.4, 0.7, visibility),
        landmark("right_hip", 0.6, 0.7, visibility),
    ]


def poor_posture_landmarks(visibility: float = 1.0) -> list[Landmark]:
    return [
        landmark("nose", 0.7, 0.25, visibility),  # far forward relative to shoulders
        landmark("left_shoulder", 0.4, 0.4, visibility),
        landmark("right_shoulder", 0.6, 0.4, visibility),
        landmark("left_hip", 0.4, 0.7, visibility),
        landmark("right_hip", 0.6, 0.7, visibility),
    ]


def confirm(analyzer: PostureAnalyzer, landmarks: list[Landmark], session_id, timestamp, n=5):
    events = []
    for _ in range(n):
        events = analyzer.update(landmarks, session_id, timestamp)
    return events


def test_missing_landmarks_yields_no_events() -> None:
    analyzer = PostureAnalyzer()
    events = analyzer.update([landmark("nose", 0.5, 0.2)], uuid4(), T0)
    assert events == []


def test_requires_confirm_frames_before_emitting_transition() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()
    landmarks = good_posture_landmarks()

    for _ in range(4):
        assert analyzer.update(landmarks, session_id, T0) == []

    events = analyzer.update(landmarks, session_id, T0)
    assert len(events) == 1
    assert events[0].type == EventType.GOOD_POSTURE


def test_poor_posture_detected_from_neck_angle() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()

    events = confirm(analyzer, poor_posture_landmarks(), session_id, T0)

    assert len(events) == 1
    assert events[0].type == EventType.POOR_POSTURE
    assert events[0].metadata["neck_angle_deg"] > 25.0


def test_transition_only_fires_once_while_state_holds() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()
    landmarks = good_posture_landmarks()

    confirm(analyzer, landmarks, session_id, T0)
    events = analyzer.update(landmarks, session_id, T0)  # 6th consecutive good frame

    assert events == []


def test_good_to_poor_transition_after_confirmed_good() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()

    confirm(analyzer, good_posture_landmarks(), session_id, T0)
    events = confirm(analyzer, poor_posture_landmarks(), session_id, T0)

    assert len(events) == 1
    assert events[0].type == EventType.POOR_POSTURE


def test_slump_started_after_sustained_poor_posture() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()

    confirm(
        analyzer, poor_posture_landmarks(), session_id, T0
    )  # confirms POOR_POSTURE, starts timer
    events = analyzer.update(poor_posture_landmarks(), session_id, T0 + timedelta(seconds=61))

    assert len(events) == 1
    assert events[0].type == EventType.SLUMP_STARTED


def test_slump_ended_with_duration_when_posture_recovers() -> None:
    analyzer = PostureAnalyzer()
    session_id = uuid4()

    confirm(analyzer, poor_posture_landmarks(), session_id, T0)
    analyzer.update(poor_posture_landmarks(), session_id, T0 + timedelta(seconds=61))

    recover_time = T0 + timedelta(seconds=90)
    events = confirm(analyzer, good_posture_landmarks(), session_id, recover_time)

    slump_ended = [e for e in events if e.type == EventType.SLUMP_ENDED]
    assert len(slump_ended) == 1
    assert slump_ended[0].duration_ms == 90_000


def test_low_confidence_landmarks_are_suppressed() -> None:
    analyzer = PostureAnalyzer(confidence_threshold=0.6)
    session_id = uuid4()

    events = confirm(analyzer, good_posture_landmarks(visibility=0.1), session_id, T0)

    assert len(events) == 1
    assert events[0].type == EventType.LOW_CONFIDENCE_SUPPRESSED
    assert events[0].metadata["original_type"] == EventType.GOOD_POSTURE.value
