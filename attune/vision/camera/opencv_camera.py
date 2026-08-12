from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import cast

import cv2

from attune.vision.camera.types import CapturedFrame, FrameArray

logger = logging.getLogger(__name__)


class OpenCVCamera:
    """ICamera implementation backed by cv2.VideoCapture.

    VideoCapture.read() blocks, so capture runs on a dedicated thread and hands
    frames to the asyncio loop via call_soon_threadsafe — the event loop is never
    blocked on hardware I/O (see docs/architecture/01-overview.md §5).
    """

    def __init__(
        self, device_index: int = 0, width: int = 1280, height: int = 720, fps: int = 30
    ) -> None:
        self._device_index = device_index
        self._width = width
        self._height = height
        self._fps = fps
        self._capture: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._queue: asyncio.Queue[CapturedFrame | None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False
        self._frame_id = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _open_capture(self) -> cv2.VideoCapture:
        # Device enumeration/opening is blocking I/O — offloaded to a thread
        # in start() below so it doesn't stall the event loop (and therefore
        # the whole API) for however long the OS takes to hand back a handle.
        capture = cv2.VideoCapture(self._device_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        capture.set(cv2.CAP_PROP_FPS, self._fps)
        return capture

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=4)
        self._frame_id = 0
        self._capture = await self._loop.run_in_executor(None, self._open_capture)

        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            raise ConnectionError(f"could not open camera at device index {self._device_index}")

        self._connected = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    async def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._connected = False

    def _capture_loop(self) -> None:
        assert self._capture is not None
        assert self._loop is not None
        assert self._queue is not None
        while not self._stop_event.is_set():
            ok, image = self._capture.read()
            if not ok:
                self._connected = False
                self._loop.call_soon_threadsafe(self._enqueue, None)
                return
            self._frame_id += 1
            frame = cast(FrameArray, image)
            captured = CapturedFrame(
                image=frame,
                frame_id=self._frame_id,
                captured_at=cv2.getTickCount() / cv2.getTickFrequency(),
            )
            self._loop.call_soon_threadsafe(self._enqueue, captured)

    def _enqueue(self, captured: CapturedFrame | None) -> None:
        assert self._queue is not None
        if self._queue.full():
            with suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
        self._queue.put_nowait(captured)

    async def frames(self) -> AsyncIterator[CapturedFrame]:
        assert self._queue is not None
        while self._connected or not self._queue.empty():
            item = await self._queue.get()
            if item is None:
                raise ConnectionError("OpenCVCamera: capture stream ended unexpectedly")
            yield item
