from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

MODEL_URLS: dict[str, str] = {
    "pose_landmarker_lite.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    ),
}


def ensure_model(name: str, model_dir: Path) -> Path:
    """Returns the local path to a MediaPipe Tasks model bundle, downloading it
    into model_dir on first use. Model files aren't bundled with the mediapipe
    pip package, so this lazily fetches them from Google's public model store.
    """
    if name not in MODEL_URLS:
        raise ValueError(f"unknown model asset {name!r}")

    model_dir.mkdir(parents=True, exist_ok=True)
    destination = model_dir / name
    if destination.exists():
        return destination

    logger.info("Downloading model asset %s", name)
    tmp_path = destination.with_suffix(destination.suffix + ".part")
    with httpx.stream("GET", MODEL_URLS[name], timeout=30.0, follow_redirects=True) as response:
        response.raise_for_status()
        with tmp_path.open("wb") as fh:
            for chunk in response.iter_bytes():
                fh.write(chunk)
    tmp_path.replace(destination)
    return destination
