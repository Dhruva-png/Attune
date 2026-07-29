from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import BoundingBox
from attune.vision.camera.types import FrameArray

PHONE_LABEL = "cell phone"


def yolo_boxes_to_detections(
    boxes_xyxyn: list[tuple[float, float, float, float]],
    confidences: list[float],
    class_ids: list[int],
    names: dict[int, str],
    min_confidence: float = 0.0,
) -> list[Detection]:
    detections: list[Detection] = []
    for (x_min, y_min, x_max, y_max), conf, cls_id in zip(
        boxes_xyxyn, confidences, class_ids, strict=True
    ):
        if conf < min_confidence:
            continue
        detections.append(
            Detection(
                label=names[cls_id],
                confidence=conf,
                bbox=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
            )
        )
    return detections


class YOLOObjectModel:
    """IObjectModel implementation backed by Ultralytics YOLO.

    Runs the full pretrained COCO-80 detector rather than a phone-only model —
    "cell phone" is already one of the 80 classes at no extra training cost,
    alongside others later features may want (e.g. "cup" for coffee-break
    detection). Callers filter to the labels they care about.
    """

    def __init__(
        self,
        model_dir: Path,
        weights_name: str = "yolov8n.pt",
        min_confidence: float = 0.5,
    ) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)
        self._model = YOLO(str(model_dir / weights_name))
        self._min_confidence = min_confidence

    def infer(self, frame: FrameArray) -> list[Detection]:
        result = self._model.predict(frame, verbose=False)[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        return yolo_boxes_to_detections(
            boxes.xyxyn.tolist(),
            boxes.conf.tolist(),
            [int(c) for c in boxes.cls.tolist()],
            result.names,
            self._min_confidence,
        )

    def close(self) -> None:
        pass  # ultralytics YOLO holds no unmanaged resources; kept for interface parity
