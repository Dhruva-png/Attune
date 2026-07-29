from __future__ import annotations

from attune.vision.objects.model import PHONE_LABEL, yolo_boxes_to_detections

NAMES = {0: "person", 41: "cup", 67: "cell phone"}


def test_empty_boxes_yields_no_detections() -> None:
    assert yolo_boxes_to_detections([], [], [], NAMES) == []


def test_converts_boxes_to_detections_with_resolved_labels() -> None:
    detections = yolo_boxes_to_detections(
        boxes_xyxyn=[(0.1, 0.2, 0.3, 0.4)],
        confidences=[0.87],
        class_ids=[67],
        names=NAMES,
    )

    assert len(detections) == 1
    d = detections[0]
    assert d.label == PHONE_LABEL
    assert d.confidence == 0.87
    assert (d.bbox.x_min, d.bbox.y_min, d.bbox.x_max, d.bbox.y_max) == (0.1, 0.2, 0.3, 0.4)


def test_multiple_boxes_are_all_converted_in_order() -> None:
    detections = yolo_boxes_to_detections(
        boxes_xyxyn=[(0.0, 0.0, 0.1, 0.1), (0.5, 0.5, 0.6, 0.6)],
        confidences=[0.9, 0.6],
        class_ids=[0, 41],
        names=NAMES,
    )

    assert [d.label for d in detections] == ["person", "cup"]


def test_boxes_below_min_confidence_are_filtered_out() -> None:
    detections = yolo_boxes_to_detections(
        boxes_xyxyn=[(0.0, 0.0, 0.1, 0.1), (0.5, 0.5, 0.6, 0.6)],
        confidences=[0.9, 0.2],
        class_ids=[67, 67],
        names=NAMES,
        min_confidence=0.5,
    )

    assert len(detections) == 1
    assert detections[0].confidence == 0.9
