from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from attune.behaviour.breaks.engine import AwayDetector
from attune.core.events.schema import EventType

T0 = datetime(2026, 1, 1, 9, 0, 0)


def test_brief_absence_does_not_trigger_left_desk() -> None:
    detector = AwayDetector()
    session_id = uuid4()

    for i in range(3):  # below ABSENCE_CONFIRM_FRAMES
        events = detector.update(False, session_id, T0 + timedelta(seconds=i))
        assert events == []

    events = detector.update(True, session_id, T0 + timedelta(seconds=3))
    assert events == []


def test_sustained_absence_triggers_left_desk() -> None:
    detector = AwayDetector()
    session_id = uuid4()

    events: list = []
    for i in range(5):
        events = detector.update(False, session_id, T0 + timedelta(seconds=i))

    assert len(events) == 1
    assert events[0].type == EventType.LEFT_DESK


def test_returned_fires_with_duration_after_presence_confirmed() -> None:
    detector = AwayDetector()
    session_id = uuid4()

    for i in range(5):
        detector.update(False, session_id, T0 + timedelta(seconds=i))

    return_start = T0 + timedelta(seconds=60)
    events: list = []
    for i in range(3):
        events = detector.update(True, session_id, return_start + timedelta(seconds=i))

    returned = [e for e in events if e.type == EventType.RETURNED]
    assert len(returned) == 1
    assert returned[0].duration_ms == 62_000  # away_since=T0, returned confirmed at T0+62s


def test_break_statistics_accumulate_across_cycles() -> None:
    detector = AwayDetector()
    session_id = uuid4()

    def leave_and_return(away_start: datetime, away_seconds: float) -> None:
        for i in range(5):
            detector.update(False, session_id, away_start + timedelta(seconds=i))
        return_start = away_start + timedelta(seconds=away_seconds)
        for i in range(3):
            detector.update(True, session_id, return_start + timedelta(seconds=i))

    leave_and_return(T0, away_seconds=10)
    leave_and_return(T0 + timedelta(seconds=100), away_seconds=30)

    assert detector.break_count == 2
    assert detector.total_break_seconds == 44  # 12s first break + 32s second break
    assert detector.longest_break_seconds == 32  # second break: 30 + 2 confirm-frame seconds
    assert detector.average_break_seconds == 22


def test_low_confidence_absence_is_suppressed() -> None:
    detector = AwayDetector(confidence_threshold=0.8)
    session_id = uuid4()

    events: list = []
    for i in range(5):
        events = detector.update(False, session_id, T0 + timedelta(seconds=i), confidence=0.5)

    assert len(events) == 1
    assert events[0].type == EventType.LOW_CONFIDENCE_SUPPRESSED
