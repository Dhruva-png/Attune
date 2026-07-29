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
        source_module: str = "vision.pipeline",
    ) -> None:
        self._camera = camera
        self._event_bus = event_bus
        self._preprocessor = preprocessor or Preprocessor()
        self._fps_governor = fps_governor or FPSGovernor(target_fps=8)
        self._frame_processors = list(frame_processors)
        self._source_module = source_module
        self._processed_frame_count = 0

    @property
    def processed_frame_count(self) -> int:
        return self._processed_frame_count

    async def run(self, session_id: UUID) -> None:
        await self._camera.start()
        try:
            async for captured in self._camera.frames():
                now = time.monotonic()
                if not self._fps_governor.should_process(now):
                    continue
                processed_image = self._preprocessor.process(captured.image)
                for processor in self._frame_processors:
                    processor(processed_image)
                self._processed_frame_count += 1
        except ConnectionError as exc:
            await self._publish_camera_disconnected(session_id, str(exc))
        finally:
            await self._camera.stop()

    async def _publish_camera_disconnected(self, session_id: UUID, reason: str) -> None:
        event = Event(
            session_id=session_id,
            type=EventType.CAMERA_DISCONNECTED,
            confidence=1.0,
            metadata={"reason": reason},
            source_module=self._source_module,
        )
        await self._event_bus.publish(event)
