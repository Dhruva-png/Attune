from __future__ import annotations

from dataclasses import dataclass

from attune.core.value_objects.geometry import BoundingBox


@dataclass(frozen=True, slots=True)
class Detection:
    label: str
    confidence: float
    bbox: BoundingBox
