from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from attune.vision.camera.mock_camera import blank_frame
from attune.vision.face.model import MediaPipeFaceModel
from attune.vision.hands.model import MediaPipeHandModel
from attune.vision.pose.model import MediaPipePoseModel

# Reused across local runs so the ~17MB of model assets aren't re-downloaded every time.
MODEL_DIR = Path("data/models")
LATENCY_BUDGET_SECONDS = 0.3  # 5 FPS floor of the spec's 5-10 FPS inference target, with margin
WARMUP_FRAMES = 2
MEASURED_FRAMES = 5


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.parametrize(
    "model_factory",
    [
        lambda: MediaPipePoseModel(MODEL_DIR),
        lambda: MediaPipeFaceModel(MODEL_DIR),
        lambda: MediaPipeHandModel(MODEL_DIR),
    ],
    ids=["pose", "face", "hand"],
)
def test_inference_meets_latency_budget(model_factory: Callable[[], object]) -> None:
    model = model_factory()
    frame = blank_frame(width=640, height=480)
    try:
        for _ in range(WARMUP_FRAMES):
            model.infer(frame)  # type: ignore[attr-defined]

        start = time.perf_counter()
        for _ in range(MEASURED_FRAMES):
            model.infer(frame)  # type: ignore[attr-defined]
        elapsed = time.perf_counter() - start

        avg_latency = elapsed / MEASURED_FRAMES
        assert avg_latency < LATENCY_BUDGET_SECONDS, (
            f"average inference latency {avg_latency:.3f}s exceeds "
            f"{LATENCY_BUDGET_SECONDS:.3f}s budget (5 FPS floor)"
        )
    finally:
        model.close()  # type: ignore[attr-defined]
