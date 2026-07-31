from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from attune.behaviour.focus.engine import FocusEngine
from attune.core.events.schema import EventType
from attune.core.value_objects.geometry import Landmark, Point
from attune.vision.face.signals import LEFT_EYE_INDICES, RIGHT_EYE_INDICES

T0 = datetime(2026, 1, 1, 9, 0, 0)
FACE_COUNT = 400


def make_face_landmarks(
    nose: tuple[float, float] = (0.5, 0.5),
    left_eye: tuple[float, float] = (0.35, 0.5),
    right_eye: tuple[float, float] = (0.65, 0.5),
) -> list[Landmark]:
    overrides: dict[int, tuple[float, float]] = {4: nose}
    for i in LEFT_EYE_INDICES:
        overrides[i] = left_eye
    for i in RIGHT_EYE_INDICES:
        overrides[i] = right_eye
    return [
        Landmark(name=f"landmark_{i}", point=Point(*overrides.get(i, (0.9, 0.9)), 0.0))
        for i in range(FACE_COUNT)
    ]


LOOKING_STRAIGHT = make_face_landmarks()
LOOKING_AWAY = make_face_landmarks(nose=(0.5, 0.5), left_eye=(0.35, 0.5), right_eye=(0.55, 0.5))


def score_of(events: list) -> float:
    return next(e for e in events if e.type == EventType.FOCUS_SCORE_UPDATED).metadata["score"]


def test_absent_yields_zero_score() -> None:
    engine = FocusEngine()
    events = engine.update([], False, None, False, uuid4(), T0)
    assert score_of(events) == 0.0


def test_present_symmetric_gaze_yields_high_score() -> None:
    engine = FocusEngine()
    events = engine.update(LOOKING_STRAIGHT, True, True, False, uuid4(), T0)
    assert score_of(events) > 90.0


def test_asymmetric_gaze_lowers_score_relative_to_symmetric() -> None:
    engine_a = FocusEngine()
    engine_b = FocusEngine()
    straight_score = score_of(engine_a.update(LOOKING_STRAIGHT, True, True, False, uuid4(), T0))
    away_score = score_of(engine_b.update(LOOKING_AWAY, True, True, False, uuid4(), T0))

    assert away_score < straight_score


def test_phone_activity_lowers_score() -> None:
    engine_a = FocusEngine()
    engine_b = FocusEngine()
    no_phone = score_of(engine_a.update(LOOKING_STRAIGHT, True, True, False, uuid4(), T0))
    with_phone = score_of(engine_b.update(LOOKING_STRAIGHT, True, True, True, uuid4(), T0))

    assert with_phone < no_phone


def test_poor_posture_lowers_score() -> None:
    engine_a = FocusEngine()
    engine_b = FocusEngine()
    good = score_of(engine_a.update(LOOKING_STRAIGHT, True, True, False, uuid4(), T0))
    poor = score_of(engine_b.update(LOOKING_STRAIGHT, True, False, False, uuid4(), T0))

    assert poor < good


def test_looking_at_screen_fires_after_confirm_frames() -> None:
    engine = FocusEngine()
    session_id = uuid4()

    events: list = []
    for _ in range(5):
        events = engine.update(LOOKING_STRAIGHT, True, True, False, session_id, T0)

    assert EventType.LOOKING_AT_SCREEN in [e.type for e in events]


def test_looked_away_then_return_reports_duration() -> None:
    engine = FocusEngine()
    session_id = uuid4()

    for _ in range(5):
        engine.update(LOOKING_STRAIGHT, True, True, False, session_id, T0)

    away_time = T0 + timedelta(seconds=10)
    for i in range(5):
        engine.update(LOOKING_AWAY, True, True, False, session_id, away_time + timedelta(seconds=i))

    return_time = away_time + timedelta(seconds=30)
    events: list = []
    for i in range(5):
        events = engine.update(
            LOOKING_STRAIGHT, True, True, False, session_id, return_time + timedelta(seconds=i)
        )

    looking_events = [e for e in events if e.type == EventType.LOOKING_AT_SCREEN]
    assert len(looking_events) == 1
    assert looking_events[0].duration_ms is not None
    assert looking_events[0].duration_ms > 0
