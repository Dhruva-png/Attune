from __future__ import annotations

import numpy as np
from attune.api.frame_overlay import draw_overlays, encode_jpeg
from attune.core.value_objects.detection import Detection, TrackedDetection
from attune.core.value_objects.geometry import BoundingBox, Landmark, Point


def _frame() -> np.ndarray:
    return np.zeros((240, 320, 3), dtype=np.uint8)


def _landmark(name: str, x: float, y: float, visibility: float = 1.0) -> Landmark:
    return Landmark(name=name, point=Point(x, y, 0.0), visibility=visibility)


def test_draw_overlays_with_no_detections_returns_unchanged_copy() -> None:
    frame = _frame()
    annotated = draw_overlays(
        frame, pose_landmarks=[], face_landmarks=[], hand_landmarks=[], phone_tracks=[]
    )
    assert annotated.shape == frame.shape
    assert annotated is not frame
    assert np.array_equal(annotated, frame)


def test_draw_overlays_does_not_mutate_the_input_frame() -> None:
    frame = _frame()
    original = frame.copy()
    pose = [_landmark("left_shoulder", 0.3, 0.3), _landmark("right_shoulder", 0.7, 0.3)]

    draw_overlays(frame, pose_landmarks=pose, face_landmarks=[], hand_landmarks=[], phone_tracks=[])

    assert np.array_equal(frame, original)


def test_draw_overlays_draws_something_when_pose_landmarks_present() -> None:
    frame = _frame()
    pose = [_landmark("left_shoulder", 0.3, 0.3), _landmark("right_shoulder", 0.7, 0.3)]

    annotated = draw_overlays(
        frame, pose_landmarks=pose, face_landmarks=[], hand_landmarks=[], phone_tracks=[]
    )

    assert not np.array_equal(annotated, frame)


def test_draw_overlays_skips_low_visibility_landmarks() -> None:
    frame = _frame()
    pose = [_landmark("left_shoulder", 0.5, 0.5, visibility=0.1)]

    annotated = draw_overlays(
        frame, pose_landmarks=pose, face_landmarks=[], hand_landmarks=[], phone_tracks=[]
    )

    assert np.array_equal(annotated, frame)


def test_draw_overlays_draws_phone_bounding_box() -> None:
    frame = _frame()
    tracked = TrackedDetection(
        detection=Detection(
            label="cell phone",
            confidence=0.9,
            bbox=BoundingBox(x_min=0.2, y_min=0.2, x_max=0.4, y_max=0.5),
        ),
        track_id=1,
        frames_tracked=3,
    )

    annotated = draw_overlays(
        frame, pose_landmarks=[], face_landmarks=[], hand_landmarks=[], phone_tracks=[tracked]
    )

    assert not np.array_equal(annotated, frame)


def test_encode_jpeg_produces_valid_jpeg_bytes() -> None:
    frame = np.full((240, 320, 3), 128, dtype=np.uint8)
    jpeg_bytes = encode_jpeg(frame)
    assert jpeg_bytes.startswith(b"\xff\xd8")  # JPEG magic bytes
    assert len(jpeg_bytes) > 0


def test_encode_jpeg_swaps_red_and_blue_channels() -> None:
    # A pure-red RGB frame should encode as a pure-red JPEG once correctly
    # converted to BGR — decoding it back and checking the dominant channel
    # is a cheap way to confirm the RGB->BGR conversion actually happened.
    import cv2

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    frame[:, :, 0] = 255  # pure red in RGB order

    jpeg_bytes = encode_jpeg(frame, quality=100)
    decoded_bgr = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    assert decoded_bgr[:, :, 2].mean() > decoded_bgr[:, :, 0].mean()  # red channel dominant in BGR
