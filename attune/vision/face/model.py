from __future__ import annotations

from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarkerResult

from attune.core.value_objects.geometry import Landmark, Point
from attune.vision.camera.types import FrameArray
from attune.vision.model_assets import ensure_model


def face_result_to_landmarks(result: FaceLandmarkerResult) -> list[Landmark]:
    if not result.face_landmarks:
        return []
    detected = result.face_landmarks[0]  # primary face
    return [
        Landmark(
            name=f"landmark_{i}",
            point=Point(lm.x, lm.y, lm.z),
            visibility=lm.visibility if lm.visibility is not None else 1.0,
        )
        for i, lm in enumerate(detected)
    ]


class MediaPipeFaceModel:
    """IFaceModel implementation backed by MediaPipe's FaceLandmarker Task.

    Returns raw mesh landmarks only (positionally indexed, name f"landmark_{i}");
    derived signals (eye/mouth aspect ratio) live in attune.vision.face.signals,
    kept separate from inference so they're testable without a loaded model.
    """

    def __init__(self, model_dir: Path, min_detection_confidence: float = 0.5) -> None:
        model_path = ensure_model("face_landmarker.task", model_dir)
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=min_detection_confidence,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._next_timestamp_ms = 0

    def infer(self, frame: FrameArray) -> list[Landmark]:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        timestamp_ms = self._next_timestamp_ms
        self._next_timestamp_ms += 1
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        return face_result_to_landmarks(result)

    def close(self) -> None:
        self._landmarker.close()
