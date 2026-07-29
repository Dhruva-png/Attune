from __future__ import annotations

from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import BoundingBox
from attune.vision.tracking.iou_tracker import IOUTracker, iou


def box(x_min: float, y_min: float, x_max: float, y_max: float) -> BoundingBox:
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)


def det(label: str, b: BoundingBox, confidence: float = 0.9) -> Detection:
    return Detection(label=label, confidence=confidence, bbox=b)


def test_iou_of_identical_boxes_is_one() -> None:
    b = box(0, 0, 10, 10)
    assert iou(b, b) == 1.0


def test_iou_of_non_overlapping_boxes_is_zero() -> None:
    assert iou(box(0, 0, 1, 1), box(5, 5, 6, 6)) == 0.0


def test_iou_of_partial_overlap() -> None:
    # two 10x10 boxes overlapping in a 5x10 region: intersection=50, union=150
    score = iou(box(0, 0, 10, 10), box(5, 0, 15, 10))
    assert abs(score - 50 / 150) < 1e-9


def test_new_detection_gets_a_new_track_id() -> None:
    tracker = IOUTracker()
    tracked = tracker.update([det("cell phone", box(0, 0, 10, 10))])
    assert len(tracked) == 1
    assert tracked[0].track_id == 1
    assert tracked[0].frames_tracked == 1


def test_same_position_next_frame_keeps_same_track_id() -> None:
    tracker = IOUTracker()
    first = tracker.update([det("cell phone", box(0, 0, 10, 10))])
    second = tracker.update([det("cell phone", box(0.5, 0.5, 10.5, 10.5))])

    assert second[0].track_id == first[0].track_id
    assert second[0].frames_tracked == 2


def test_track_survives_a_brief_missed_frame_then_rematches() -> None:
    tracker = IOUTracker(max_frames_since_seen=2)
    first = tracker.update([det("cell phone", box(0, 0, 10, 10))])

    tracker.update([])  # missed frame — track kept alive internally

    third = tracker.update([det("cell phone", box(0, 0, 10, 10))])

    assert third[0].track_id == first[0].track_id


def test_track_dropped_after_exceeding_max_frames_since_seen() -> None:
    tracker = IOUTracker(max_frames_since_seen=1)
    first = tracker.update([det("cell phone", box(0, 0, 10, 10))])

    tracker.update([])  # miss 1 (still alive)
    tracker.update([])  # miss 2 (exceeds grace period, dropped)

    reappeared = tracker.update([det("cell phone", box(0, 0, 10, 10))])

    assert reappeared[0].track_id != first[0].track_id


def test_missed_frame_track_is_not_returned_to_caller() -> None:
    tracker = IOUTracker(max_frames_since_seen=2)
    tracker.update([det("cell phone", box(0, 0, 10, 10))])

    missed = tracker.update([])

    assert missed == []


def test_different_labels_never_match_even_with_full_overlap() -> None:
    tracker = IOUTracker()
    first = tracker.update([det("cell phone", box(0, 0, 10, 10))])
    second = tracker.update([det("cup", box(0, 0, 10, 10))])

    assert second[0].track_id != first[0].track_id
    assert second[0].frames_tracked == 1


def test_multiple_simultaneous_detections_get_distinct_track_ids() -> None:
    tracker = IOUTracker()
    tracked = tracker.update(
        [
            det("cell phone", box(0, 0, 10, 10)),
            det("cell phone", box(50, 50, 60, 60)),
        ]
    )
    assert {t.track_id for t in tracked} == {1, 2}


def test_low_overlap_below_threshold_starts_a_new_track() -> None:
    tracker = IOUTracker(iou_threshold=0.5)
    first = tracker.update([det("cell phone", box(0, 0, 10, 10))])
    # shifted far enough that IOU < 0.5
    second = tracker.update([det("cell phone", box(8, 8, 18, 18))])

    assert second[0].track_id != first[0].track_id
