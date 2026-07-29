from __future__ import annotations

from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from attune.vision.camera.types import FrameArray


def resize(frame: FrameArray, width: int, height: int) -> FrameArray:
    return cast(FrameArray, cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA))


def to_rgb(frame: FrameArray) -> FrameArray:
    return cast(FrameArray, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def normalize(frame: FrameArray) -> NDArray[np.float32]:
    return (frame.astype(np.float32) / 255.0).astype(np.float32)


def denoise(frame: FrameArray, strength: int = 5) -> FrameArray:
    return cast(
        FrameArray, cv2.fastNlMeansDenoisingColored(frame, None, strength, strength, 7, 21)
    )
