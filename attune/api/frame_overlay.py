from __future__ import annotations

import cv2

from attune.vision.camera.types import FrameArray


def encode_jpeg(frame: FrameArray, quality: int = 80) -> bytes:
    """Encodes a raw camera frame (BGR, as delivered by OpenCVCamera) to JPEG
    for the live dashboard preview. No color conversion needed — cv2.imencode
    already expects BGR."""
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("failed to encode frame as JPEG")
    return bytes(buffer)
