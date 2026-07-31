from __future__ import annotations

import math
from collections import deque
from datetime import datetime, timedelta
from uuid import UUID

from attune.behaviour.confidence import gate
from attune.core.entities.fatigue import FatigueLevel
from attune.core.events.schema import Event, EventType
from attune.core.value_objects.geometry import Landmark
from attune.vision.face.signals import (
    LEFT_EYE_INDICES,
    MOUTH_INDICES,
    RIGHT_EYE_INDICES,
    eye_aspect_ratio,
    mouth_aspect_ratio,
)

EYE_CLOSED_THRESHOLD = 0.2
LONG_BLINK_MS = 400
YAWN_THRESHOLD = 0.5
YAWN_MIN_DURATION_MS = 500
FACE_TOUCH_DISTANCE = 0.08
FACE_REFERENCE_LANDMARK_INDEX = 4  # nose tip in the 468-point face mesh topology
BLINK_RATE_WINDOW_SECONDS = 60.0

# Nose tip is only reachable when a full 468-point mesh was detected.
MIN_FACE_LANDMARKS = FACE_REFERENCE_LANDMARK_INDEX + 1


class FatigueEngine:
    """Turns face/hand landmarks into YAWN, LONG_BLINK, FACE_TOUCH, and
    FATIGUE_LEVEL_CHANGED events. Blink rate and yawn/face-touch counts are
    tracked over a rolling window and combined into a FatigueLevel — the
    exact thresholds are a documented starting point (see module constants),
    not a calibrated clinical model.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        source_module: str = "behaviour.fatigue",
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._source_module = source_module

        self._eye_closed_since: datetime | None = None
        self._blink_timestamps: deque[datetime] = deque()
        self._long_blink_timestamps: deque[datetime] = deque()

        self._yawn_started_at: datetime | None = None
        self._yawn_fired = False
        self._yawn_timestamps: deque[datetime] = deque()

        self._is_touching_face = False
        self._face_touch_timestamps: deque[datetime] = deque()

        self._level: FatigueLevel | None = None

    def update(
        self,
        face_landmarks: list[Landmark],
        hand_landmarks: list[Landmark],
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        events: list[Event] = []
        confidence = self._face_confidence(face_landmarks)

        events.extend(self._evaluate_blink(face_landmarks, confidence, session_id, timestamp))
        events.extend(self._evaluate_yawn(face_landmarks, confidence, session_id, timestamp))
        events.extend(
            self._evaluate_face_touch(
                face_landmarks, hand_landmarks, confidence, session_id, timestamp
            )
        )
        events.extend(self._evaluate_fatigue_level(confidence, session_id, timestamp))

        return [gate(event, self._confidence_threshold) for event in events]

    @staticmethod
    def _face_confidence(face_landmarks: list[Landmark]) -> float:
        if len(face_landmarks) < MIN_FACE_LANDMARKS:
            return 0.0
        return sum(lm.visibility for lm in face_landmarks) / len(face_landmarks)

    def _prune(self, window: deque[datetime], timestamp: datetime, seconds: float) -> None:
        cutoff = timestamp - timedelta(seconds=seconds)
        while window and window[0] < cutoff:
            window.popleft()

    def _evaluate_blink(
        self,
        face_landmarks: list[Landmark],
        confidence: float,
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        if len(face_landmarks) <= max(max(LEFT_EYE_INDICES), max(RIGHT_EYE_INDICES)):
            return []

        ear = (
            eye_aspect_ratio(face_landmarks, LEFT_EYE_INDICES)
            + eye_aspect_ratio(face_landmarks, RIGHT_EYE_INDICES)
        ) / 2.0
        is_closed = ear < EYE_CLOSED_THRESHOLD

        events: list[Event] = []
        if is_closed and self._eye_closed_since is None:
            self._eye_closed_since = timestamp
        elif not is_closed and self._eye_closed_since is not None:
            duration_ms = int((timestamp - self._eye_closed_since).total_seconds() * 1000)
            self._blink_timestamps.append(timestamp)
            self._eye_closed_since = None
            if duration_ms >= LONG_BLINK_MS:
                self._long_blink_timestamps.append(timestamp)
                events.append(
                    Event(
                        session_id=session_id,
                        type=EventType.LONG_BLINK,
                        timestamp=timestamp,
                        confidence=confidence,
                        duration_ms=duration_ms,
                        metadata={"eye_aspect_ratio": ear},
                        source_module=self._source_module,
                    )
                )

        self._prune(self._blink_timestamps, timestamp, BLINK_RATE_WINDOW_SECONDS)
        self._prune(self._long_blink_timestamps, timestamp, BLINK_RATE_WINDOW_SECONDS)
        return events

    def _evaluate_yawn(
        self,
        face_landmarks: list[Landmark],
        confidence: float,
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        if len(face_landmarks) <= max(MOUTH_INDICES):
            return []

        mar = mouth_aspect_ratio(face_landmarks, MOUTH_INDICES)
        is_open = mar > YAWN_THRESHOLD

        events: list[Event] = []
        if is_open:
            if self._yawn_started_at is None:
                self._yawn_started_at = timestamp
                self._yawn_fired = False
            elapsed_ms = (timestamp - self._yawn_started_at).total_seconds() * 1000
            if elapsed_ms >= YAWN_MIN_DURATION_MS and not self._yawn_fired:
                self._yawn_fired = True
                self._yawn_timestamps.append(timestamp)
                events.append(
                    Event(
                        session_id=session_id,
                        type=EventType.YAWN,
                        timestamp=timestamp,
                        confidence=confidence,
                        metadata={"mouth_aspect_ratio": mar},
                        source_module=self._source_module,
                    )
                )
        else:
            self._yawn_started_at = None
            self._yawn_fired = False

        self._prune(self._yawn_timestamps, timestamp, BLINK_RATE_WINDOW_SECONDS)
        return events

    def _evaluate_face_touch(
        self,
        face_landmarks: list[Landmark],
        hand_landmarks: list[Landmark],
        confidence: float,
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        if len(face_landmarks) <= FACE_REFERENCE_LANDMARK_INDEX or not hand_landmarks:
            self._is_touching_face = False
            return []

        reference = face_landmarks[FACE_REFERENCE_LANDMARK_INDEX].point
        is_touching = any(
            math.dist((reference.x, reference.y), (hand.point.x, hand.point.y))
            < FACE_TOUCH_DISTANCE
            for hand in hand_landmarks
        )

        events: list[Event] = []
        if is_touching and not self._is_touching_face:
            self._face_touch_timestamps.append(timestamp)
            events.append(
                Event(
                    session_id=session_id,
                    type=EventType.FACE_TOUCH,
                    timestamp=timestamp,
                    confidence=confidence,
                    source_module=self._source_module,
                )
            )
        self._is_touching_face = is_touching

        self._prune(self._face_touch_timestamps, timestamp, BLINK_RATE_WINDOW_SECONDS)
        return events

    def _evaluate_fatigue_level(
        self, confidence: float, session_id: UUID, timestamp: datetime
    ) -> list[Event]:
        blink_rate = len(self._blink_timestamps) / (BLINK_RATE_WINDOW_SECONDS / 60.0)
        yawn_count = len(self._yawn_timestamps)
        long_blink_count = len(self._long_blink_timestamps)
        face_touch_count = len(self._face_touch_timestamps)

        signals: list[str] = []
        if yawn_count >= 3 or blink_rate > 30:
            level = FatigueLevel.VERY_TIRED
        elif yawn_count >= 1 or blink_rate > 20 or long_blink_count >= 2:
            level = FatigueLevel.TIRED
        elif blink_rate > 12 or face_touch_count >= 2:
            level = FatigueLevel.NORMAL
        else:
            level = FatigueLevel.FRESH

        if yawn_count:
            signals.append("yawning")
        if long_blink_count:
            signals.append("long_blinks")
        if blink_rate > 12:
            signals.append("elevated_blink_rate")
        if face_touch_count:
            signals.append("face_touching")

        if level == self._level:
            return []

        from_level = self._level
        self._level = level
        return [
            Event(
                session_id=session_id,
                type=EventType.FATIGUE_LEVEL_CHANGED,
                timestamp=timestamp,
                confidence=confidence,
                metadata={
                    "from_level": from_level.value if from_level else None,
                    "to_level": level.value,
                    "contributing_signals": signals,
                    "blink_rate_per_minute": blink_rate,
                },
                source_module=self._source_module,
            )
        ]
