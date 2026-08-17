from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import UUID

from attune.api.frame_overlay import encode_jpeg
from attune.behaviour.breaks.engine import AwayDetector
from attune.behaviour.fatigue.engine import FatigueEngine
from attune.behaviour.focus.engine import FocusEngine
from attune.behaviour.phone.engine import PhoneInteractionEngine
from attune.behaviour.posture.engine import PostureAnalyzer
from attune.core.events.schema import Event
from attune.core.interfaces.bus import IEventBus
from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import Landmark
from attune.vision.camera.opencv_camera import OpenCVCamera
from attune.vision.camera.types import FrameArray
from attune.vision.face.model import MediaPipeFaceModel
from attune.vision.hands.model import MediaPipeHandModel
from attune.vision.objects.model import PHONE_LABEL, YOLOObjectModel
from attune.vision.pipeline import VisionPipeline
from attune.vision.pose.model import MediaPipePoseModel
from attune.vision.tracking.iou_tracker import IOUTracker
from attune.vision.tracking.phone_presence import PhonePresenceTracker

logger = logging.getLogger(__name__)

# Lower than YOLOObjectModel's own default (0.5) — a phone held at an angle or
# partially out of frame often lands in the 0.35-0.5 band, and missing those
# is exactly what "the phone thing doesn't seem to be working" reports.
# PhonePresenceTracker still debounces by track_id, so this doesn't spam events.
_PHONE_DETECTION_CONFIDENCE = 0.35

# Halving each capture dimension cuts pixels (and therefore MediaPipe/YOLO
# inference cost) to a quarter of the camera's 1280x720 default — the
# dominant lever for keeping a CPU-only laptop responsive during a session.
_CAMERA_WIDTH = 640
_CAMERA_HEIGHT = 480

# YOLO alone costs ~4-5x as much as pose+face+hand combined (measured ~90ms
# vs ~40ms on a 4-core/8-thread laptop CPU) despite being one of four models
# run per frame — it dominates the per-frame budget. Phone presence doesn't
# need frame-perfect updates the way head-pose/focus tracking does, so it
# only runs every Nth processed frame; pose/face/hand still run every frame.
# Detections are held over the skipped frames so the phone tracker/overlay
# don't flicker between "seen" and "gone" every cycle.
_YOLO_FRAME_STRIDE = 3


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
        self._latest_frames: dict[UUID, bytes] = {}

    def is_active(self, session_id: UUID) -> bool:
        return session_id in self._tasks

    def get_latest_frame(self, session_id: UUID) -> bytes | None:
        return self._latest_frames.get(session_id)

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
            self._latest_frames.pop(session_id, None)

    def _load_models(
        self,
    ) -> tuple[MediaPipePoseModel, MediaPipeFaceModel, MediaPipeHandModel, YOLOObjectModel]:
        # Loading four model files from disk is real blocking I/O+CPU work —
        # run off the event loop so starting a session doesn't freeze the
        # API (and therefore the dashboard). Constructed sequentially: an
        # earlier version loaded all four concurrently across threads for a
        # much faster startup, but MediaPipe/TFLite's native runtime isn't
        # guaranteed safe for concurrent construction either, and that
        # change landed in the same build where posture/phone detection
        # broke — reverted along with the concurrent per-frame inference
        # change for the same reason (see run_models below).
        return (
            MediaPipePoseModel(self._model_dir),
            MediaPipeFaceModel(self._model_dir),
            MediaPipeHandModel(self._model_dir),
            YOLOObjectModel(self._model_dir, min_confidence=_PHONE_DETECTION_CONFIDENCE),
        )

    async def _run_unsafe(self, session_id: UUID, camera_index: int) -> None:
        loop = asyncio.get_running_loop()
        camera = OpenCVCamera(device_index=camera_index, width=_CAMERA_WIDTH, height=_CAMERA_HEIGHT)
        pose_model, face_model, hand_model, object_model = await loop.run_in_executor(
            None, self._load_models
        )
        tracker = IOUTracker()
        # Separate from `tracker` above: that one feeds PhoneInteractionEngine
        # (hand-proximity pickup/putdown transitions), this one feeds
        # PhonePresenceTracker (fires once per new phone sighting regardless
        # of hand proximity) — two different behavioural questions over the
        # same detections, so they need independent per-track debounce state.
        phone_presence = PhonePresenceTracker()

        focus_engine = FocusEngine(confidence_threshold=self._confidence_threshold)
        fatigue_engine = FatigueEngine(confidence_threshold=self._confidence_threshold)
        posture_analyzer = PostureAnalyzer(confidence_threshold=self._confidence_threshold)
        phone_engine = PhoneInteractionEngine(confidence_threshold=self._confidence_threshold)
        away_detector = AwayDetector(confidence_threshold=self._confidence_threshold)

        # Four model inferences per frame is real CPU work (hundreds of ms on
        # a laptop CPU) — running it synchronously on this coroutine would
        # block the event loop, and the API runs in-process on the *same*
        # loop the Qt GUI uses (qasync), so the whole window would freeze on
        # every processed frame. frame_processors only ever hands off the
        # latest frame; the actual inference happens in a thread via
        # run_in_executor, keeping the UI responsive no matter how slow
        # inference is. A full queue means inference is still busy with the
        # previous frame, so the stale one is dropped rather than queued —
        # same graceful-degradation principle as FrameBuffer.
        frame_queue: asyncio.Queue[FrameArray] = asyncio.Queue(maxsize=1)
        processed_frame_count = 0
        last_detections: list[Detection] = []

        def enqueue_frame(frame: FrameArray) -> None:
            if frame_queue.full():
                with suppress(asyncio.QueueEmpty):
                    frame_queue.get_nowait()
            frame_queue.put_nowait(frame)

        def store_preview_frame(frame: FrameArray) -> None:
            # Runs on every raw captured frame, ahead of the FPS governor
            # that throttles inference — the preview should track the
            # camera's real capture rate, not the much slower rate the four
            # models can sustain. Plain camera feed, no overlays: what the
            # models see stays an internal detail, not something drawn on
            # screen. JPEG-encoding a frame is cheap (a few ms) so this runs
            # inline rather than needing its own executor hop.
            self._latest_frames[session_id] = encode_jpeg(frame)

        def run_models(
            frame: FrameArray, run_yolo: bool
        ) -> tuple[list[Landmark], list[Landmark], list[Landmark], list[Detection] | None]:
            # Called sequentially within a single executor thread. An
            # earlier version dispatched pose/face/hand/YOLO to separate
            # threads via asyncio.gather to run them concurrently — that
            # measured faster in isolated benchmarks, but broke posture and
            # phone detection in real use: MediaPipe/TFLite's native runtime
            # isn't guaranteed safe for truly concurrent inference calls
            # across model instances that share an internal thread pool, and
            # landmark results came back wrong under real concurrent load in
            # a way a quick timing benchmark didn't surface. Reverted to
            # sequential; only the YOLO stride skip (below) still saves time.
            pose_landmarks = pose_model.infer(frame)
            face_landmarks = face_model.infer(frame)
            hand_landmarks = hand_model.infer(frame)
            detections = object_model.infer(frame) if run_yolo else None
            return pose_landmarks, face_landmarks, hand_landmarks, detections

        async def run_inference(frame: FrameArray) -> list[Event]:
            nonlocal processed_frame_count, last_detections
            timestamp = datetime.utcnow()

            processed_frame_count += 1
            run_yolo = processed_frame_count % _YOLO_FRAME_STRIDE == 0
            (
                pose_landmarks,
                face_landmarks,
                hand_landmarks,
                yolo_result,
            ) = await loop.run_in_executor(None, run_models, frame, run_yolo)
            if yolo_result is not None:
                last_detections = yolo_result
            detections = last_detections

            tracked = tracker.update(detections)
            phone_tracks = [t for t in tracked if t.detection.label == PHONE_LABEL]
            is_present = bool(pose_landmarks)

            events = [
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
            presence_event = phone_presence.update(detections, session_id)
            if presence_event is not None:
                events.append(presence_event)

            return events

        async def process_frames() -> None:
            while True:
                frame = await frame_queue.get()
                for event in await run_inference(frame):
                    await self._event_bus.publish(event)

        pipeline = VisionPipeline(
            camera,
            self._event_bus,
            frame_processors=[enqueue_frame],
            raw_frame_processors=[store_preview_frame],
        )
        process_task = asyncio.ensure_future(process_frames())
        try:
            await pipeline.run(session_id)
        finally:
            process_task.cancel()
            with suppress(asyncio.CancelledError):
                await process_task
            for model in (pose_model, face_model, hand_model, object_model):
                model.close()
