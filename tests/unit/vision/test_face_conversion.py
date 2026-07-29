from __future__ import annotations

from attune.vision.face.model import face_result_to_landmarks
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarkerResult


def make_landmark(
    x: float, y: float, z: float, visibility: float | None = None
) -> NormalizedLandmark:
    return NormalizedLandmark(x=x, y=y, z=z, visibility=visibility, presence=visibility)


def test_no_face_detected_yields_empty_list() -> None:
    result = FaceLandmarkerResult(
        face_landmarks=[], face_blendshapes=[], facial_transformation_matrixes=[]
    )
    assert face_result_to_landmarks(result) == []


def test_converts_mesh_landmarks_with_positional_names() -> None:
    detected = [make_landmark(i * 0.001, i * 0.002, 0.0) for i in range(478)]
    result = FaceLandmarkerResult(
        face_landmarks=[detected], face_blendshapes=[], facial_transformation_matrixes=[]
    )

    landmarks = face_result_to_landmarks(result)

    assert len(landmarks) == 478
    assert landmarks[0].name == "landmark_0"
    assert landmarks[477].name == "landmark_477"
    assert landmarks[10].point.x == 10 * 0.001


def test_unset_visibility_defaults_to_fully_visible() -> None:
    result = FaceLandmarkerResult(
        face_landmarks=[[make_landmark(0.0, 0.0, 0.0, visibility=None)]],
        face_blendshapes=[],
        facial_transformation_matrixes=[],
    )

    landmarks = face_result_to_landmarks(result)

    assert landmarks[0].visibility == 1.0
