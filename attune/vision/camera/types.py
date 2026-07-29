from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FrameArray = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    image: FrameArray
    frame_id: int
    captured_at: float
