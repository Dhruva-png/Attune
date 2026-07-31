from __future__ import annotations

from datetime import datetime
from uuid import UUID

from attune.behaviour.confidence import gate
from attune.core.events.schema import Event, EventType

ABSENCE_CONFIRM_FRAMES = 5
PRESENCE_CONFIRM_FRAMES = 3


class AwayDetector:
    """Turns a per-frame presence signal into LEFT_DESK / RETURNED events,
    debounced so a single missed detection doesn't register as a break.
    Tracks running break statistics for the analytics layer to read.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        source_module: str = "behaviour.breaks",
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._source_module = source_module

        self._is_away = False
        self._away_since: datetime | None = None
        self._consecutive_absent = 0
        self._consecutive_present = 0

        self.break_count = 0
        self.total_break_seconds = 0.0
        self.longest_break_seconds = 0.0

    @property
    def average_break_seconds(self) -> float:
        return self.total_break_seconds / self.break_count if self.break_count else 0.0

    def update(
        self,
        is_present: bool,
        session_id: UUID,
        timestamp: datetime,
        confidence: float = 0.9,
    ) -> list[Event]:
        if is_present:
            return self._handle_present(session_id, timestamp, confidence)
        return self._handle_absent(session_id, timestamp, confidence)

    def _handle_present(
        self, session_id: UUID, timestamp: datetime, confidence: float
    ) -> list[Event]:
        self._consecutive_present += 1
        self._consecutive_absent = 0

        if not self._is_away or self._consecutive_present < PRESENCE_CONFIRM_FRAMES:
            return []

        assert self._away_since is not None
        duration = (timestamp - self._away_since).total_seconds()
        self._is_away = False
        self._away_since = None
        self.break_count += 1
        self.total_break_seconds += duration
        self.longest_break_seconds = max(self.longest_break_seconds, duration)

        event = Event(
            session_id=session_id,
            type=EventType.RETURNED,
            timestamp=timestamp,
            confidence=confidence,
            duration_ms=int(duration * 1000),
            source_module=self._source_module,
        )
        return [gate(event, self._confidence_threshold)]

    def _handle_absent(
        self, session_id: UUID, timestamp: datetime, confidence: float
    ) -> list[Event]:
        self._consecutive_absent += 1
        self._consecutive_present = 0

        if self._consecutive_absent == 1:
            self._away_since = timestamp

        if self._is_away or self._consecutive_absent < ABSENCE_CONFIRM_FRAMES:
            return []

        self._is_away = True
        event = Event(
            session_id=session_id,
            type=EventType.LEFT_DESK,
            timestamp=timestamp,
            confidence=confidence,
            source_module=self._source_module,
        )
        return [gate(event, self._confidence_threshold)]
