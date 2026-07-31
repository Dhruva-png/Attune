from __future__ import annotations

from datetime import datetime
from uuid import UUID

from attune.behaviour.confidence import gate
from attune.core.events.schema import Event, EventType
from attune.core.value_objects.detection import TrackedDetection
from attune.core.value_objects.geometry import Landmark

HAND_PROXIMITY_MARGIN = 0.05  # normalized-coordinate expansion around the phone bbox
GLANCE_MAX_SECONDS = 3.0
SHORT_MAX_SECONDS = 30.0


def _is_hand_near_phone(hand_landmarks: list[Landmark], tracked: TrackedDetection) -> bool:
    bbox = tracked.detection.bbox
    x_min, y_min = bbox.x_min - HAND_PROXIMITY_MARGIN, bbox.y_min - HAND_PROXIMITY_MARGIN
    x_max, y_max = bbox.x_max + HAND_PROXIMITY_MARGIN, bbox.y_max + HAND_PROXIMITY_MARGIN
    return any(
        x_min <= hand.point.x <= x_max and y_min <= hand.point.y <= y_max for hand in hand_landmarks
    )


def classify_interaction(duration_seconds: float) -> str:
    if duration_seconds <= GLANCE_MAX_SECONDS:
        return "glance"
    if duration_seconds <= SHORT_MAX_SECONDS:
        return "short"
    return "extended"


class PhoneInteractionEngine:
    """Classifies phone visibility (from vision.tracking) as held-in-hand or
    not, based on hand-landmark proximity to the tracked phone's bounding
    box. Emits PHONE_PICKUP on pickup and PHONE_DOWN (with duration and a
    glance/short/extended classification) on release — the behavioural
    judgment layer that vision.tracking.PhonePresenceTracker deliberately
    leaves for M5 to own.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        source_module: str = "behaviour.phone",
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._source_module = source_module
        self._is_held = False
        self._pickup_at: datetime | None = None

    def update(
        self,
        phone_detections: list[TrackedDetection],
        hand_landmarks: list[Landmark],
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        held_candidates = [t for t in phone_detections if _is_hand_near_phone(hand_landmarks, t)]
        is_held = bool(held_candidates)

        if is_held and not self._is_held:
            return self._pickup(held_candidates, session_id, timestamp)
        if not is_held and self._is_held:
            return self._put_down(session_id, timestamp)
        return []

    def _pickup(
        self, held_candidates: list[TrackedDetection], session_id: UUID, timestamp: datetime
    ) -> list[Event]:
        self._is_held = True
        self._pickup_at = timestamp
        primary = max(held_candidates, key=lambda t: t.detection.confidence)
        event = Event(
            session_id=session_id,
            type=EventType.PHONE_PICKUP,
            timestamp=timestamp,
            confidence=primary.detection.confidence,
            metadata={"track_id": primary.track_id},
            source_module=self._source_module,
        )
        return [gate(event, self._confidence_threshold)]

    def _put_down(self, session_id: UUID, timestamp: datetime) -> list[Event]:
        assert self._pickup_at is not None
        duration_seconds = (timestamp - self._pickup_at).total_seconds()
        self._is_held = False
        self._pickup_at = None

        event = Event(
            session_id=session_id,
            type=EventType.PHONE_DOWN,
            timestamp=timestamp,
            confidence=0.9,
            duration_ms=int(duration_seconds * 1000),
            metadata={"interaction_class": classify_interaction(duration_seconds)},
            source_module=self._source_module,
        )
        return [gate(event, self._confidence_threshold)]
