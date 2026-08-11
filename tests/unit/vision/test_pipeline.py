from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from attune.core.events.bus import EventBus
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.bus import EventHandler
from attune.vision.camera.fps_governor import FPSGovernor
from attune.vision.camera.mock_camera import MockCamera, blank_frame
from attune.vision.camera.types import CapturedFrame, FrameArray
from attune.vision.pipeline import VisionPipeline


class _FlakyCamera:
    """Raises ConnectionError on the first frames() call, then yields
    normally after being stopped and restarted — exercises the pipeline's
    one-shot reconnect path for a transient glitch (e.g. a USB power blip).
    """

    def __init__(self, frame_count: int = 3) -> None:
        self._frame_count = frame_count
        self._start_count = 0
        self._connected = False

    async def start(self) -> None:
        self._start_count += 1
        self._connected = True

    async def stop(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def frames(self) -> AsyncIterator[CapturedFrame]:
        if self._start_count == 1:
            raise ConnectionError("FlakyCamera: simulated one-time disconnect")
        for i in range(self._frame_count):
            yield CapturedFrame(image=blank_frame(), frame_id=i + 1, captured_at=i * 0.033)


class _NeverReconnectsCamera:
    """Succeeds on the very first start() (so the pipeline can begin), then
    fails every start() after that — simulates a camera that's actually
    gone, not just glitching, so the reconnect attempt itself fails."""

    def __init__(self) -> None:
        self._start_count = 0
        self._connected = False

    async def start(self) -> None:
        self._start_count += 1
        if self._start_count > 1:
            raise ConnectionError("camera permanently unavailable")
        self._connected = True

    async def stop(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def frames(self) -> AsyncIterator[CapturedFrame]:
        # An unreachable yield keeps this an async generator function so
        # `async for` works, even though the body always raises first.
        if self._start_count < 0:
            yield CapturedFrame(image=blank_frame(), frame_id=0, captured_at=0.0)
        raise ConnectionError("initial disconnect")


def _collector(events: list[Event]) -> EventHandler:
    async def handler(event: Event) -> None:
        events.append(event)

    return handler


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


@pytest.mark.asyncio
async def test_pipeline_reconnects_and_resumes_after_a_transient_disconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_clock = itertools.count(start=0, step=10.0)
    monkeypatch.setattr("attune.vision.pipeline.time.monotonic", lambda: next(fake_clock))

    camera = _FlakyCamera(frame_count=3)
    bus = EventBus()
    disconnected: list[Event] = []
    reconnected: list[Event] = []
    bus.subscribe(EventType.CAMERA_DISCONNECTED, _collector(disconnected))
    bus.subscribe(EventType.CAMERA_RECONNECTED, _collector(reconnected))
    session_id = uuid4()
    pipeline = VisionPipeline(camera, bus)

    await pipeline.run(session_id=session_id)  # must not raise

    assert disconnected == []
    assert len(reconnected) == 1
    assert reconnected[0].session_id == session_id
    assert (
        reconnected[0].metadata["previous_reason"]
        == "FlakyCamera: simulated one-time disconnect"
    )
    assert pipeline.processed_frame_count == 3
    assert camera.is_connected is False  # stopped cleanly at the end of the session


@pytest.mark.asyncio
async def test_pipeline_gives_up_when_reconnect_attempt_itself_fails() -> None:
    camera = _NeverReconnectsCamera()
    bus = EventBus()
    disconnected: list[Event] = []
    reconnected: list[Event] = []
    bus.subscribe(EventType.CAMERA_DISCONNECTED, _collector(disconnected))
    bus.subscribe(EventType.CAMERA_RECONNECTED, _collector(reconnected))
    session_id = uuid4()
    pipeline = VisionPipeline(camera, bus)

    await pipeline.run(session_id=session_id)  # must not raise

    assert reconnected == []
    assert len(disconnected) == 1
    assert disconnected[0].metadata["reason"] == "initial disconnect"
