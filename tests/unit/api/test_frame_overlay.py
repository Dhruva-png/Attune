from __future__ import annotations

import cv2
import numpy as np
from attune.api.frame_overlay import encode_jpeg


def test_encode_jpeg_produces_valid_jpeg_bytes() -> None:
    frame = np.full((240, 320, 3), 128, dtype=np.uint8)
    jpeg_bytes = encode_jpeg(frame)
    assert jpeg_bytes.startswith(b"\xff\xd8")  # JPEG magic bytes
    assert len(jpeg_bytes) > 0


def test_encode_jpeg_preserves_bgr_channel_order() -> None:
    # No color conversion should happen — the frame is already BGR (as
    # OpenCVCamera delivers it), and cv2.imencode expects BGR directly.
    # A pure-blue BGR frame (channel 0) should decode back with blue
    # dominant, not swapped to red.
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    frame[:, :, 0] = 255  # pure blue in BGR order

    jpeg_bytes = encode_jpeg(frame, quality=100)
    decoded = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    assert decoded[:, :, 0].mean() > decoded[:, :, 2].mean()  # blue channel dominant
