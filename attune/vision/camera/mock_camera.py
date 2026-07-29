from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable

import numpy as np

from attune.vision.camera.types import CapturedFrame, FrameArray


def blank_frame(width: int = 640, height: int = 480) -> FrameArray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class MockCamera:
    """ICamera test/demo double — never touches real hardware, so vision-pipeline
    tests and CI run without a webcam (docs/architecture/08-roadmap.md M2).
    """

    def __init__(
        self,
        frames: Iterable[FrameArray] | None = None,
        *,
        frame_count: int = 5,
        fail_after: int | None = None,
    ) -> None:
        self._source_frames = (
            list(frames) if frames is not None else [blank_frame() for _ in range(frame_count)]
        )
        self._fail_after = fail_after
        self._connected = False
        self._frame_id = 0

    async def start(self) -> None:
        self._connected = True
        self._frame_id = 0

    async def stop(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def frames(self) -> AsyncIterator[CapturedFrame]:
        for image in self._source_frames:
            if not self._connected:
                return
            if self._fail_after is not None and self._frame_id >= self._fail_after:
                self._connected = False
                raise ConnectionError("MockCamera: simulated disconnect")
            self._frame_id += 1
            yield CapturedFrame(
                image=image, frame_id=self._frame_id, captured_at=self._frame_id * 0.033
            )
            await asyncio.sleep(0)
