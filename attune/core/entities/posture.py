from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PostureMetric:
    neck_angle_deg: float
    shoulder_delta_px: float
    forward_lean_deg: float
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
