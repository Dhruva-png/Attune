from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FatigueLevel(StrEnum):
    FRESH = "fresh"
    NORMAL = "normal"
    TIRED = "tired"
    VERY_TIRED = "very_tired"


@dataclass(frozen=True, slots=True)
class FatigueState:
    level: FatigueLevel
    confidence: float
    contributing_signals: tuple[str, ...] = ()
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be within [0, 1], got {self.confidence}")
