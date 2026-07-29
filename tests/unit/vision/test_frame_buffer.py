from __future__ import annotations

import pytest
from attune.vision.camera.buffer import FrameBuffer
from attune.vision.camera.mock_camera import blank_frame
from attune.vision.camera.types import CapturedFrame


def make_frame(frame_id: int) -> CapturedFrame:
    return CapturedFrame(image=blank_frame(), frame_id=frame_id, captured_at=frame_id * 0.033)


@pytest.mark.asyncio
async def test_put_and_get_preserve_order_within_capacity() -> None:
    buffer = FrameBuffer(maxsize=4)
    await buffer.put(make_frame(1))
    await buffer.put(make_frame(2))

    assert (await buffer.get()).frame_id == 1
    assert (await buffer.get()).frame_id == 2


@pytest.mark.asyncio
async def test_overflow_drops_oldest_frame() -> None:
    buffer = FrameBuffer(maxsize=2)
    await buffer.put(make_frame(1))
    await buffer.put(make_frame(2))
    await buffer.put(make_frame(3))  # should drop frame 1

    assert buffer.dropped_count == 1
    assert (await buffer.get()).frame_id == 2
    assert (await buffer.get()).frame_id == 3


@pytest.mark.asyncio
async def test_qsize_reflects_buffered_frames() -> None:
    buffer = FrameBuffer(maxsize=4)
    assert buffer.qsize() == 0
    await buffer.put(make_frame(1))
    assert buffer.qsize() == 1
