from __future__ import annotations

import pytest
from attune.vision.camera.mock_camera import MockCamera


@pytest.mark.asyncio
async def test_yields_configured_frame_count() -> None:
    camera = MockCamera(frame_count=5)
    await camera.start()

    collected = [frame async for frame in camera.frames()]

    assert len(collected) == 5
    assert [f.frame_id for f in collected] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_is_connected_transitions_with_start_and_stop() -> None:
    camera = MockCamera(frame_count=1)
    assert camera.is_connected is False

    await camera.start()
    assert camera.is_connected is True

    await camera.stop()
    assert camera.is_connected is False


@pytest.mark.asyncio
async def test_fail_after_raises_connection_error_and_disconnects() -> None:
    camera = MockCamera(frame_count=5, fail_after=3)
    await camera.start()

    collected = []
    with pytest.raises(ConnectionError):
        async for frame in camera.frames():
            collected.append(frame)

    assert [f.frame_id for f in collected] == [1, 2, 3]
    assert camera.is_connected is False
