from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from uuid import UUID

from attune.core.events.schema import Event, EventType
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.camera import ICamera
from attune.vision.camera.fps_governor import FPSGovernor
from attune.vision.camera.types import FrameArray
from attune.vision.preprocessing.pipeline import Preprocessor

FrameProcessor = Callable[[FrameArray], None]

# A webcam glitch (USB power blip, driver hiccup) is common and usually
# transient — one reconnect attempt covers that case without turning a
# genuinely unplugged/removed camera into a retry loop.
MAX_RECONNECT_ATTEMPTS = 1


class VisionPipeline:
    """Orchestrates camera -> preprocessing -> model inference -> events.

    Model stages (pose/face/hands/objects) are injected as frame processors and
    default to empty here; each publishes its own events onto the bus once wired
    in later milestones (docs/architecture/08-roadmap.md M3/M4).
    """

    def __init__(
        self,
        camera: ICamera,
        event_bus: IEventBus,
        *,
        preprocessor: Preprocessor | None = None,
        fps_governor: FPSGovernor | None = None,
        frame_processors: Sequence[FrameProcessor] = (),
        raw_frame_processors: Sequence[FrameProcessor] = (),
        source_module: str = "vision.pipeline",
    ) -> None:
        self._camera = camera
        self._event_bus = event_bus
        self._preprocessor = preprocessor or Preprocessor()
        self._fps_governor = fps_governor or FPSGovernor(target_fps=8)
        self._frame_processors = list(frame_processors)
        # Unlike frame_processors, these run on every captured frame ahead of
        # the FPS governor gate — for consumers like a live preview that want
        # to track the camera's real capture rate rather than the (much
        # lower) rate inference can sustain.
        self._raw_frame_processors = list(raw_frame_processors)
        self._source_module = source_module
        self._processed_frame_count = 0

    @property
    def processed_frame_count(self) -> int:
        return self._processed_frame_count

    async def run(self, session_id: UUID) -> None:
        await self._camera.start()
        try:
            await self._consume_frames(session_id)
        finally:
            await self._camera.stop()

    async def _consume_frames(self, session_id: UUID) -> None:
        reconnect_attempts_left = MAX_RECONNECT_ATTEMPTS
        while True:
            try:
                await self._process_frame_stream()
                return  # camera ended the stream normally (e.g. session stop)
            except ConnectionError as exc:
                if reconnect_attempts_left <= 0 or not await self._try_reconnect(
                    session_id, str(exc)
                ):
                    await self._publish_camera_disconnected(session_id, str(exc))
                    return
                reconnect_attempts_left -= 1

    async def _process_frame_stream(self) -> None:
        async for captured in self._camera.frames():
            for raw_processor in self._raw_frame_processors:
                raw_processor(captured.image)

            now = time.monotonic()
            if not self._fps_governor.should_process(now):
                continue
            processed_image = self._preprocessor.process(captured.image)
            for processor in self._frame_processors:
                processor(processed_image)
            self._processed_frame_count += 1

    async def _try_reconnect(self, session_id: UUID, reason: str) -> bool:
        await self._camera.stop()
        try:
            await self._camera.start()
        except ConnectionError:
            return False
        await self._publish_camera_reconnected(session_id, reason)
        return True

    async def _publish_camera_disconnected(self, session_id: UUID, reason: str) -> None:
        event = Event(
            session_id=session_id,
            type=EventType.CAMERA_DISCONNECTED,
            confidence=1.0,
            metadata={"reason": reason},
            source_module=self._source_module,
        )
        await self._event_bus.publish(event)

    async def _publish_camera_reconnected(self, session_id: UUID, previous_reason: str) -> None:
        event = Event(
            session_id=session_id,
            type=EventType.CAMERA_RECONNECTED,
            confidence=1.0,
            metadata={"previous_reason": previous_reason},
            source_module=self._source_module,
        )
        await self._event_bus.publish(event)
