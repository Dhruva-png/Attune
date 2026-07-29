from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FocusScore:
    value: float  # 0-100
    gaze_factor: float
    posture_factor: float
    phone_factor: float
    presence_factor: float
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise ValueError(f"FocusScore must be within [0, 100], got {self.value}")
