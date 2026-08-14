from __future__ import annotations

from unittest.mock import AsyncMock

import numpy as np
import pytest
from attune.api.frame_overlay import encode_jpeg
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.live_view_model import LiveViewModel
from attune.dashboard.views.live_view import NO_SESSION_MESSAGE, LiveView
from PySide6.QtWidgets import QApplication


def _real_jpeg_bytes() -> bytes:
    # A real encoded JPEG, not a mock — QPixmap.loadFromData is a Qt/PySide6
    # runtime API, and a previous regression here (passing an explicit
    # format hint) only surfaced against real bytes: it type-checked fine
    # and any mocked byte string would have hidden the bug too.
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    return encode_jpeg(frame)


@pytest.fixture
def live_view(qt_app: QApplication) -> LiveView:
    api_client = AsyncMock(spec=ApiClient)
    view_model = LiveViewModel(api_client)
    return LiveView(view_model)


def test_frame_updated_renders_a_real_jpeg_into_the_camera_label(live_view: LiveView) -> None:
    live_view._view_model.frame_updated.emit(_real_jpeg_bytes())

    pixmap = live_view._camera_label.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()


def test_frame_unavailable_clears_the_pixmap_and_restores_the_placeholder(
    live_view: LiveView,
) -> None:
    live_view._view_model.frame_updated.emit(_real_jpeg_bytes())

    live_view._view_model.frame_unavailable.emit()

    assert live_view._camera_label.pixmap().isNull()
    assert live_view._camera_label.text() == NO_SESSION_MESSAGE


def test_frame_updated_with_garbage_bytes_does_not_raise(live_view: LiveView) -> None:
    live_view._view_model.frame_updated.emit(b"not a jpeg")
