from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Confidence:
    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be within [0, 1], got {self.value}")

    def is_reliable(self, threshold: float) -> bool:
        return self.value >= threshold
