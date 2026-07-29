from __future__ import annotations

from dataclasses import dataclass

from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import BoundingBox
from attune.vision.tracking.types import TrackedDetection


def iou(a: BoundingBox, b: BoundingBox) -> float:
    x_min = max(a.x_min, b.x_min)
    y_min = max(a.y_min, b.y_min)
    x_max = min(a.x_max, b.x_max)
    y_max = min(a.y_max, b.y_max)

    intersection = max(0.0, x_max - x_min) * max(0.0, y_max - y_min)
    if intersection <= 0.0:
        return 0.0

    union = a.width * a.height + b.width * b.height - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


@dataclass(slots=True)
class _Track:
    track_id: int
    detection: Detection
    frames_tracked: int
    frames_since_seen: int


class IOUTracker:
    """Greedy IOU-matching multi-object tracker.

    Assigns stable track_ids to detections across frames so downstream
    consumers can reason about object persistence (e.g. "is this the same
    phone as 2 frames ago?"). Tracks survive briefly through missed frames
    (up to max_frames_since_seen) so a one-frame occlusion doesn't churn the
    track_id, but only tracks matched in the current frame are returned.
    """

    def __init__(self, iou_threshold: float = 0.3, max_frames_since_seen: int = 5) -> None:
        self._iou_threshold = iou_threshold
        self._max_frames_since_seen = max_frames_since_seen
        self._tracks: list[_Track] = []
        self._next_track_id = 1

    def update(self, detections: list[Detection]) -> list[TrackedDetection]:
        unmatched = list(detections)
        surviving: list[_Track] = []

        for track in self._tracks:
            best_match: Detection | None = None
            best_score = self._iou_threshold
            for det in unmatched:
                if det.label != track.detection.label:
                    continue
                score = iou(det.bbox, track.detection.bbox)
                if score > best_score:
                    best_score = score
                    best_match = det

            if best_match is not None:
                track.detection = best_match
                track.frames_tracked += 1
                track.frames_since_seen = 0
                unmatched.remove(best_match)
                surviving.append(track)
            else:
                track.frames_since_seen += 1
                if track.frames_since_seen <= self._max_frames_since_seen:
                    surviving.append(track)

        for det in unmatched:
            surviving.append(
                _Track(
                    track_id=self._next_track_id,
                    detection=det,
                    frames_tracked=1,
                    frames_since_seen=0,
                )
            )
            self._next_track_id += 1

        self._tracks = surviving

        return [
            TrackedDetection(
                detection=t.detection, track_id=t.track_id, frames_tracked=t.frames_tracked
            )
            for t in self._tracks
            if t.frames_since_seen == 0
        ]
