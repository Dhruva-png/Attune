from __future__ import annotations

import asyncio

from attune.vision.camera.types import CapturedFrame


class FrameBuffer:
    """Bounded frame queue that drops the oldest frame on overflow instead of
    growing unbounded, so inference lag degrades gracefully (see
    docs/architecture/01-overview.md §5).
    """

    def __init__(self, maxsize: int = 4) -> None:
        self._queue: asyncio.Queue[CapturedFrame] = asyncio.Queue(maxsize=maxsize)
        self._dropped_count = 0

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def qsize(self) -> int:
        return self._queue.qsize()

    async def put(self, frame: CapturedFrame) -> None:
        if self._queue.full():
            try:
                self._queue.get_nowait()
                self._dropped_count += 1
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(frame)

    async def get(self) -> CapturedFrame:
        return await self._queue.get()
