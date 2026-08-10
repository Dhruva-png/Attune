from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app() -> Iterator[QApplication]:
    """QObject/QTimer construction needs a QCoreApplication to exist.

    Signals still deliver synchronously on direct (same-thread) connections
    without a running Qt event loop, so viewmodel tests don't need qtbot —
    they just need this instance to exist somewhere in the process.
    """
    app = QApplication.instance() or QApplication([])
    yield app
