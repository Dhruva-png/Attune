from __future__ import annotations

from pathlib import Path

import cv2
import pytest
from attune.vision.objects.model import YOLOObjectModel
from ultralytics.utils import ASSETS

# ASSETS ships with the ultralytics package itself (bus.jpg, zidane.jpg) — a
# real, known-content photo to sanity-check detection against, since no
# phone-specific labeled fixture clip is available in this repo yet (tracked
# separately; see the M4 summary for what a true precision/recall test needs).
MODEL_DIR = Path("data/models")


@pytest.mark.integration
def test_detects_people_in_a_real_photo() -> None:
    frame = cv2.imread(str(Path(ASSETS) / "zidane.jpg"))
    assert frame is not None, "bundled ultralytics sample asset failed to load"

    model = YOLOObjectModel(MODEL_DIR, min_confidence=0.5)
    detections = model.infer(frame)

    labels = [d.label for d in detections]
    assert "person" in labels
    assert all(0.5 <= d.confidence <= 1.0 for d in detections)
    assert all(0.0 <= d.bbox.x_min < d.bbox.x_max <= 1.0 for d in detections)
    assert all(0.0 <= d.bbox.y_min < d.bbox.y_max <= 1.0 for d in detections)
