from __future__ import annotations

from dataclasses import dataclass

from attune.core.value_objects.detection import Detection


@dataclass(frozen=True, slots=True)
class TrackedDetection:
    detection: Detection
    track_id: int
    frames_tracked: int
