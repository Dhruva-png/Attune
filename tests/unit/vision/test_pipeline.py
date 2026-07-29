from __future__ import annotations

import itertools
from uuid import uuid4

import pytest
from attune.core.events.bus import EventBus
from attune.core.events.schema import Event, EventType
from attune.vision.camera.fps_governor import FPSGovernor
from attune.vision.camera.mock_camera import MockCamera
from attune.vision.camera.types import FrameArray
from attune.vision.pipeline import VisionPipeline


@pytest.mark.asyncio
async def test_pipeline_runs_every_frame_through_processors_when_unthrottled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Real elapsed time between loop iterations can be a fraction of a microsecond,
    # so racing the governor with a huge target_fps is flaky. Fake the clock instead:
    # each call advances far past any interval, so every frame is always processed.
    fake_clock = itertools.count(start=0, step=10.0)
    monkeypatch.setattr("attune.vision.pipeline.time.monotonic", lambda: next(fake_clock))

    camera = MockCamera(frame_count=5)
    bus = EventBus()
    seen: list[FrameArray] = []
    pipeline = VisionPipeline(camera, bus, frame_processors=[seen.append])

    await pipeline.run(session_id=uuid4())

    assert len(seen) == 5
    assert pipeline.processed_frame_count == 5


@pytest.mark.asyncio
async def test_pipeline_stops_camera_after_normal_completion() -> None:
    camera = MockCamera(frame_count=3)
    bus = EventBus()
    pipeline = VisionPipeline(camera, bus)

    await pipeline.run(session_id=uuid4())

    assert camera.is_connected is False


@pytest.mark.asyncio
async def test_pipeline_publishes_camera_disconnected_on_stream_failure() -> None:
    camera = MockCamera(frame_count=5, fail_after=2)
    bus = EventBus()
    received: list[Event] = []

    async def collector(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.CAMERA_DISCONNECTED, collector)
    session_id = uuid4()
    pipeline = VisionPipeline(camera, bus)

    await pipeline.run(session_id=session_id)  # must not raise

    assert len(received) == 1
    assert received[0].session_id == session_id
    assert received[0].metadata["reason"] == "MockCamera: simulated disconnect"
    assert camera.is_connected is False


@pytest.mark.asyncio
async def test_pipeline_governor_throttles_processing() -> None:
    camera = MockCamera(frame_count=5)
    bus = EventBus()
    seen: list[FrameArray] = []

    # Target FPS low enough that, given how fast the test loop runs, only the
    # first frame passes the governor before the interval has elapsed.
    pipeline = VisionPipeline(
        camera,
        bus,
        fps_governor=FPSGovernor(target_fps=0.001),
        frame_processors=[seen.append],
    )

    await pipeline.run(session_id=uuid4())

    assert len(seen) == 1
