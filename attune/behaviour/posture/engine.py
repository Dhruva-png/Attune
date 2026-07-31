from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from attune.behaviour.confidence import gate
from attune.core.events.schema import Event, EventType
from attune.core.value_objects.geometry import Landmark, Point

NECK_ANGLE_THRESHOLD_DEG = 25.0
FORWARD_LEAN_THRESHOLD_DEG = 15.0
CONFIRM_FRAMES = 5
SLUMP_DURATION_SECONDS = 60.0


def _midpoint(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2)


def _angle_from_vertical_deg(origin: Point, target: Point) -> float:
    dx = target.x - origin.x
    dy = target.y - origin.y
    return math.degrees(math.atan2(abs(dx), abs(dy))) if (dx or dy) else 0.0


class PostureMetrics:
    """Pure geometry: pose landmarks -> neck angle, forward lean, shoulder delta."""

    REQUIRED = ("nose", "left_shoulder", "right_shoulder", "left_hip", "right_hip")

    def __init__(self, landmarks: list[Landmark]) -> None:
        self._by_name = {lm.name: lm for lm in landmarks}

    @property
    def is_available(self) -> bool:
        return all(name in self._by_name for name in self.REQUIRED)

    @property
    def confidence(self) -> float:
        if not self.is_available:
            return 0.0
        values = [self._by_name[name].visibility for name in self.REQUIRED]
        return sum(values) / len(values)

    def compute(self) -> tuple[float, float, float]:
        """Returns (neck_angle_deg, forward_lean_deg, shoulder_delta)."""
        nose = self._by_name["nose"].point
        left_shoulder = self._by_name["left_shoulder"].point
        right_shoulder = self._by_name["right_shoulder"].point
        left_hip = self._by_name["left_hip"].point
        right_hip = self._by_name["right_hip"].point

        mid_shoulder = _midpoint(left_shoulder, right_shoulder)
        mid_hip = _midpoint(left_hip, right_hip)

        neck_angle_deg = _angle_from_vertical_deg(mid_shoulder, nose)
        forward_lean_deg = _angle_from_vertical_deg(mid_hip, mid_shoulder)
        shoulder_delta = abs(left_shoulder.y - right_shoulder.y)

        return neck_angle_deg, forward_lean_deg, shoulder_delta


class PostureAnalyzer:
    """Turns pose landmarks into GOOD_POSTURE/POOR_POSTURE and SLUMP_STARTED/
    SLUMP_ENDED events. Transitions are debounced over CONFIRM_FRAMES
    consecutive readings so single-frame landmark noise doesn't flap the
    reported state.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        source_module: str = "behaviour.posture",
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._source_module = source_module
        self._is_poor: bool | None = None
        self._pending_state: bool | None = None
        self._pending_streak = 0
        self._is_slumping = False
        self._slump_started_at: datetime | None = None

    def update(
        self, landmarks: list[Landmark], session_id: UUID, timestamp: datetime
    ) -> list[Event]:
        metrics = PostureMetrics(landmarks)
        if not metrics.is_available:
            return []

        neck_angle_deg, forward_lean_deg, shoulder_delta = metrics.compute()
        is_poor = (
            neck_angle_deg > NECK_ANGLE_THRESHOLD_DEG
            or forward_lean_deg > FORWARD_LEAN_THRESHOLD_DEG
        )
        geometry_metadata = {
            "neck_angle_deg": neck_angle_deg,
            "forward_lean_deg": forward_lean_deg,
            "shoulder_delta_px": shoulder_delta,
        }

        events = [
            *self._evaluate_transition(
                is_poor, metrics.confidence, session_id, timestamp, geometry_metadata
            ),
            *self._evaluate_slump(metrics.confidence, session_id, timestamp, geometry_metadata),
        ]
        return [gate(event, self._confidence_threshold) for event in events]

    def _evaluate_transition(
        self,
        is_poor: bool,
        confidence: float,
        session_id: UUID,
        timestamp: datetime,
        metadata: dict[str, float],
    ) -> list[Event]:
        if self._pending_state == is_poor:
            self._pending_streak += 1
        else:
            self._pending_state = is_poor
            self._pending_streak = 1

        if self._pending_streak < CONFIRM_FRAMES or self._is_poor == is_poor:
            return []

        self._is_poor = is_poor
        event_type = EventType.POOR_POSTURE if is_poor else EventType.GOOD_POSTURE
        return [
            Event(
                session_id=session_id,
                type=event_type,
                timestamp=timestamp,
                confidence=confidence,
                metadata=metadata,
                source_module=self._source_module,
            )
        ]

    def _evaluate_slump(
        self,
        confidence: float,
        session_id: UUID,
        timestamp: datetime,
        metadata: dict[str, float],
    ) -> list[Event]:
        if self._is_poor and not self._is_slumping:
            if self._slump_started_at is None:
                self._slump_started_at = timestamp
            elif (timestamp - self._slump_started_at).total_seconds() >= SLUMP_DURATION_SECONDS:
                self._is_slumping = True
                return [
                    Event(
                        session_id=session_id,
                        type=EventType.SLUMP_STARTED,
                        timestamp=timestamp,
                        confidence=confidence,
                        metadata=metadata,
                        source_module=self._source_module,
                    )
                ]
        elif not self._is_poor:
            if self._is_slumping:
                self._is_slumping = False
                assert self._slump_started_at is not None
                duration_ms = int((timestamp - self._slump_started_at).total_seconds() * 1000)
                self._slump_started_at = None
                return [
                    Event(
                        session_id=session_id,
                        type=EventType.SLUMP_ENDED,
                        timestamp=timestamp,
                        confidence=confidence,
                        duration_ms=duration_ms,
                        metadata=metadata,
                        source_module=self._source_module,
                    )
                ]
            self._slump_started_at = None

        return []
