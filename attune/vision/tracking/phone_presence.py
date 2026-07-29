from __future__ import annotations

from uuid import UUID

from attune.core.events.schema import Event, EventType
from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import BoundingBox
from attune.vision.tracking.iou_tracker import IOUTracker

PHONE_LABEL = "cell phone"


def _bbox_to_dict(bbox: BoundingBox) -> dict[str, float]:
    return {"x_min": bbox.x_min, "y_min": bbox.y_min, "x_max": bbox.x_max, "y_max": bbox.y_max}


class PhonePresenceTracker:
    """Publishes PHONE_DETECTED the first time a phone track appears, debounced
    by track_id so a phone that stays visible across many frames only fires
    once. Whether that visibility constitutes a "pickup", a glance, or extended
    use is behavioural policy — see attune.behaviour.phone (M5), which consumes
    this observation rather than vision re-implementing that judgment.
    """

    def __init__(
        self, tracker: IOUTracker | None = None, source_module: str = "vision.tracking"
    ) -> None:
        self._tracker = tracker or IOUTracker()
        self._source_module = source_module
        self._known_track_ids: set[int] = set()

    def update(self, detections: list[Detection], session_id: UUID) -> Event | None:
        phone_detections = [d for d in detections if d.label == PHONE_LABEL]
        tracked = self._tracker.update(phone_detections)

        new_tracks = [t for t in tracked if t.track_id not in self._known_track_ids]
        self._known_track_ids.update(t.track_id for t in tracked)

        if not new_tracks:
            return None

        primary = max(new_tracks, key=lambda t: t.detection.confidence)
        return Event(
            session_id=session_id,
            type=EventType.PHONE_DETECTED,
            confidence=primary.detection.confidence,
            metadata={
                "bbox": _bbox_to_dict(primary.detection.bbox),
                "track_id": primary.track_id,
            },
            source_module=self._source_module,
        )
