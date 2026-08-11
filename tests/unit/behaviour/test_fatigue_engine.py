from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from attune.behaviour.face_geometry import LEFT_EYE_INDICES, MOUTH_INDICES, RIGHT_EYE_INDICES
from attune.behaviour.fatigue.engine import FACE_REFERENCE_LANDMARK_INDEX, FatigueEngine
from attune.core.entities.fatigue import FatigueLevel
from attune.core.events.schema import EventType
from attune.core.value_objects.geometry import Landmark, Point

T0 = datetime(2026, 1, 1, 9, 0, 0)
FACE_COUNT = 400


def _eye_overrides(
    indices: tuple[int, int, int, int, int, int],
    center_x: float,
    ear_target: float,
    horizontal: float = 0.1,
) -> dict[int, tuple[float, float]]:
    p1, p2, p3, p4, p5, p6 = indices
    half_v = (ear_target * horizontal) / 2
    return {
        p1: (center_x - horizontal / 2, 0.0),
        p4: (center_x + horizontal / 2, 0.0),
        p2: (center_x - horizontal / 6, -half_v),
        p6: (center_x - horizontal / 6, half_v),
        p3: (center_x + horizontal / 6, -half_v),
        p5: (center_x + horizontal / 6, half_v),
    }


def _mouth_overrides(mar_target: float, horizontal: float = 0.1) -> dict[int, tuple[float, float]]:
    left, right, top, bottom = MOUTH_INDICES
    vertical = mar_target * horizontal
    return {
        left: (0.5 - horizontal / 2, 0.7),
        right: (0.5 + horizontal / 2, 0.7),
        top: (0.5, 0.7 - vertical / 2),
        bottom: (0.5, 0.7 + vertical / 2),
    }


def make_face_landmarks(
    *, eyes_open: bool = True, mouth_open: bool = False, visibility: float = 1.0
) -> list[Landmark]:
    overrides: dict[int, tuple[float, float]] = {}
    ear = 0.3 if eyes_open else 0.1
    overrides.update(_eye_overrides(LEFT_EYE_INDICES, center_x=0.3, ear_target=ear))
    overrides.update(_eye_overrides(RIGHT_EYE_INDICES, center_x=0.7, ear_target=ear))
    overrides.update(_mouth_overrides(mar_target=0.6 if mouth_open else 0.2))
    overrides[FACE_REFERENCE_LANDMARK_INDEX] = (0.5, 0.3)

    return [
        Landmark(
            name=f"landmark_{i}",
            point=Point(*overrides.get(i, (0.9, 0.9)), 0.0),
            visibility=visibility,
        )
        for i in range(FACE_COUNT)
    ]


def hand_at(x: float, y: float) -> list[Landmark]:
    return [Landmark(name="wrist", point=Point(x, y, 0.0), visibility=1.0)]


def test_no_face_landmarks_yields_only_a_suppressed_event() -> None:
    engine = FatigueEngine()
    events = engine.update([], [], uuid4(), T0)

    assert len(events) == 1
    assert events[0].type == EventType.LOW_CONFIDENCE_SUPPRESSED


def test_open_eyes_closed_mouth_produces_no_blink_or_yawn() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    events = engine.update(make_face_landmarks(), [], session_id, T0)

    assert EventType.YAWN not in [e.type for e in events]
    assert EventType.LONG_BLINK not in [e.type for e in events]


def test_long_blink_detected_on_reopen_after_threshold() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    engine.update(make_face_landmarks(eyes_open=False), [], session_id, T0)
    events = engine.update(
        make_face_landmarks(eyes_open=True), [], session_id, T0 + timedelta(milliseconds=500)
    )

    long_blinks = [e for e in events if e.type == EventType.LONG_BLINK]
    assert len(long_blinks) == 1
    assert long_blinks[0].duration_ms == 500


def test_short_blink_is_not_flagged_as_long() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    engine.update(make_face_landmarks(eyes_open=False), [], session_id, T0)
    events = engine.update(
        make_face_landmarks(eyes_open=True), [], session_id, T0 + timedelta(milliseconds=100)
    )

    assert EventType.LONG_BLINK not in [e.type for e in events]


def test_yawn_fires_once_after_sustained_open_mouth() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    first = engine.update(make_face_landmarks(mouth_open=True), [], session_id, T0)
    assert EventType.YAWN not in [e.type for e in first]

    second = engine.update(
        make_face_landmarks(mouth_open=True), [], session_id, T0 + timedelta(milliseconds=600)
    )
    yawns = [e for e in second if e.type == EventType.YAWN]
    assert len(yawns) == 1

    third = engine.update(
        make_face_landmarks(mouth_open=True), [], session_id, T0 + timedelta(milliseconds=700)
    )
    assert EventType.YAWN not in [e.type for e in third]


def test_face_touch_detected_once_then_reset_on_release() -> None:
    engine = FatigueEngine()
    session_id = uuid4()
    near_nose = hand_at(0.5, 0.35)  # nose tip is at (0.5, 0.3); within FACE_TOUCH_DISTANCE
    far_away = hand_at(0.9, 0.9)

    first = engine.update(make_face_landmarks(), near_nose, session_id, T0)
    assert len([e for e in first if e.type == EventType.FACE_TOUCH]) == 1

    second = engine.update(make_face_landmarks(), near_nose, session_id, T0)
    assert EventType.FACE_TOUCH not in [e.type for e in second]

    engine.update(make_face_landmarks(), far_away, session_id, T0)
    fourth = engine.update(make_face_landmarks(), near_nose, session_id, T0)
    assert len([e for e in fourth if e.type == EventType.FACE_TOUCH]) == 1


def test_fatigue_level_starts_fresh_then_becomes_tired_after_yawn() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    first = engine.update(make_face_landmarks(), [], session_id, T0)
    level_events = [e for e in first if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert len(level_events) == 1
    assert level_events[0].metadata["to_level"] == FatigueLevel.FRESH.value

    engine.update(make_face_landmarks(mouth_open=True), [], session_id, T0 + timedelta(seconds=1))
    after_yawn = engine.update(
        make_face_landmarks(mouth_open=True),
        [],
        session_id,
        T0 + timedelta(seconds=1, milliseconds=600),
    )

    level_change = [e for e in after_yawn if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert len(level_change) == 1
    assert level_change[0].metadata["to_level"] == FatigueLevel.TIRED.value
    assert "yawning" in level_change[0].metadata["contributing_signals"]


def _do_yawn(engine: FatigueEngine, session_id, start: datetime) -> list:
    engine.update(make_face_landmarks(mouth_open=True), [], session_id, start)
    events = engine.update(
        make_face_landmarks(mouth_open=True), [], session_id, start + timedelta(milliseconds=600)
    )
    # mouth closes again so the next yawn is detected as a fresh occurrence
    engine.update(
        make_face_landmarks(mouth_open=False), [], session_id, start + timedelta(milliseconds=700)
    )
    return events


def test_three_yawns_escalate_fatigue_to_very_tired() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    _do_yawn(engine, session_id, T0)
    _do_yawn(engine, session_id, T0 + timedelta(seconds=10))
    third = _do_yawn(engine, session_id, T0 + timedelta(seconds=20))

    level_change = [e for e in third if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert len(level_change) == 1
    assert level_change[0].metadata["to_level"] == FatigueLevel.VERY_TIRED.value


def _do_blink(engine: FatigueEngine, session_id, at: datetime) -> list:
    engine.update(make_face_landmarks(eyes_open=False), [], session_id, at)
    return engine.update(
        make_face_landmarks(eyes_open=True), [], session_id, at + timedelta(milliseconds=100)
    )


def test_elevated_blink_rate_is_reported_as_a_contributing_signal() -> None:
    engine = FatigueEngine()
    session_id = uuid4()

    all_events: list = []
    for i in range(13):  # >12 blinks/min crosses the "elevated_blink_rate" threshold
        all_events.extend(_do_blink(engine, session_id, T0 + timedelta(seconds=i)))

    level_changes = [e for e in all_events if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert any("elevated_blink_rate" in e.metadata["contributing_signals"] for e in level_changes)


def test_stale_fatigue_signals_age_out_of_the_rolling_window() -> None:
    # A long-running session shouldn't let an isolated cluster of fatigue
    # signals from an hour ago keep depressing the *current* reading forever.
    engine = FatigueEngine()
    session_id = uuid4()
    near_nose = hand_at(0.5, 0.35)
    far_away = hand_at(0.9, 0.9)

    engine.update(make_face_landmarks(), near_nose, session_id, T0)
    engine.update(make_face_landmarks(), far_away, session_id, T0)  # release
    escalated = engine.update(
        make_face_landmarks(), near_nose, session_id, T0 + timedelta(seconds=1)
    )
    escalation = [e for e in escalated if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert len(escalation) == 1
    assert escalation[0].metadata["to_level"] == FatigueLevel.NORMAL.value

    # Past the 60s rolling window — both prior face-touches should age out.
    later = T0 + timedelta(seconds=1, minutes=2)
    aged_out = engine.update(make_face_landmarks(), far_away, session_id, later)

    recovery = [e for e in aged_out if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    assert len(recovery) == 1
    assert recovery[0].metadata["to_level"] == FatigueLevel.FRESH.value
