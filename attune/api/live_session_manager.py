from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import UUID

from attune.behaviour.breaks.engine import AwayDetector
from attune.behaviour.fatigue.engine import FatigueEngine
from attune.behaviour.focus.engine import FocusEngine
from attune.behaviour.phone.engine import PhoneInteractionEngine
from attune.behaviour.posture.engine import PostureAnalyzer
from attune.core.events.schema import Event
from attune.core.interfaces.bus import IEventBus
from attune.vision.camera.opencv_camera import OpenCVCamera
from attune.vision.camera.types import FrameArray
from attune.vision.face.model import MediaPipeFaceModel
from attune.vision.hands.model import MediaPipeHandModel
from attune.vision.objects.model import PHONE_LABEL, YOLOObjectModel
from attune.vision.pipeline import VisionPipeline
from attune.vision.pose.model import MediaPipePoseModel
from attune.vision.tracking.iou_tracker import IOUTracker

logger = logging.getLogger(__name__)


class LiveSessionManager:
    """Wires camera capture -> MediaPipe/YOLO inference -> behaviour engines
    -> the event bus for a real webcam session, and owns the background task
    per active session.

    This is the piece that was missing end-to-end: every layer it touches
    (vision, behaviour) was built and unit-tested in isolation, but nothing
    ever actually started them together for a session created through the
    API. Kept in attune.api rather than attune.bootstrap since it's scoped to
    a single running session's lifecycle, not app-wide infrastructure wiring
    — but it plays the same "composition root" role for that lifecycle.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        model_dir: Path,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._event_bus = event_bus
        self._model_dir = model_dir
        self._confidence_threshold = confidence_threshold
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    def is_active(self, session_id: UUID) -> bool:
        return session_id in self._tasks

    def start(self, session_id: UUID, camera_index: int = 0) -> None:
        if session_id in self._tasks:
            return
        self._tasks[session_id] = asyncio.ensure_future(self._run(session_id, camera_index))

    async def stop(self, session_id: UUID) -> None:
        task = self._tasks.pop(session_id, None)
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _run(self, session_id: UUID, camera_index: int) -> None:
        try:
            await self._run_unsafe(session_id, camera_index)
        except Exception:
            logger.exception("live session %s failed", session_id)
        finally:
            self._tasks.pop(session_id, None)

    def _load_models(
        self,
    ) -> tuple[MediaPipePoseModel, MediaPipeFaceModel, MediaPipeHandModel, YOLOObjectModel]:
        # Loading four model files from disk is real blocking I/O+CPU work —
        # run off the event loop so starting a session doesn't freeze the
        # API (and therefore the dashboard, which only talks to it over
        # HTTP) for the several seconds this takes.
        return (
            MediaPipePoseModel(self._model_dir),
            MediaPipeFaceModel(self._model_dir),
            MediaPipeHandModel(self._model_dir),
            YOLOObjectModel(self._model_dir),
        )

    async def _run_unsafe(self, session_id: UUID, camera_index: int) -> None:
        loop = asyncio.get_running_loop()
        camera = OpenCVCamera(device_index=camera_index)
        pose_model, face_model, hand_model, object_model = await loop.run_in_executor(
            None, self._load_models
        )
        tracker = IOUTracker()

        focus_engine = FocusEngine(confidence_threshold=self._confidence_threshold)
        fatigue_engine = FatigueEngine(confidence_threshold=self._confidence_threshold)
        posture_analyzer = PostureAnalyzer(confidence_threshold=self._confidence_threshold)
        phone_engine = PhoneInteractionEngine(confidence_threshold=self._confidence_threshold)
        away_detector = AwayDetector(confidence_threshold=self._confidence_threshold)

        event_queue: asyncio.Queue[Event] = asyncio.Queue()

        def process_frame(frame: FrameArray) -> None:
            timestamp = datetime.utcnow()
            pose_landmarks = pose_model.infer(frame)
            face_landmarks = face_model.infer(frame)
            hand_landmarks = hand_model.infer(frame)
            tracked = tracker.update(object_model.infer(frame))
            phone_tracks = [t for t in tracked if t.detection.label == PHONE_LABEL]
            is_present = bool(pose_landmarks)

            events: list[Event] = [
                *posture_analyzer.update(pose_landmarks, session_id, timestamp),
                *away_detector.update(is_present, session_id, timestamp),
                *phone_engine.update(phone_tracks, hand_landmarks, session_id, timestamp),
                *fatigue_engine.update(face_landmarks, hand_landmarks, session_id, timestamp),
                *focus_engine.update(
                    face_landmarks,
                    is_present,
                    posture_analyzer.posture_is_good,
                    phone_engine.is_held,
                    session_id,
                    timestamp,
                ),
            ]
            for event in events:
                event_queue.put_nowait(event)

        async def drain_events() -> None:
            while True:
                event = await event_queue.get()
                await self._event_bus.publish(event)

        pipeline = VisionPipeline(camera, self._event_bus, frame_processors=[process_frame])
        drain_task = asyncio.ensure_future(drain_events())
        try:
            await pipeline.run(session_id)
        finally:
            # Flush anything still queued before tearing down so a stop()
            # right after a frame finishes doesn't silently drop its events.
            while not event_queue.empty():
                await self._event_bus.publish(event_queue.get_nowait())
            drain_task.cancel()
            with suppress(asyncio.CancelledError):
                await drain_task
            for model in (pose_model, face_model, hand_model, object_model):
                model.close()
