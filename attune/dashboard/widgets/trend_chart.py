from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from attune.dashboard.theme.tokens import PALETTE


class TrendChart(QWidget):
    """Minimal native line chart for a series of values.

    A deliberately simple alternative to embedding Plotly/QWebEngine for
    this first dashboard pass — richer interactive charts are a natural
    extension once the reporting pipeline needs Plotly anyway (M11).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self.setMinimumHeight(120)

    def set_values(self, values: list[float]) -> None:
        self._values = values
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if len(self._values) < 2:
            painter.setPen(QColor(PALETTE.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Not enough data yet")
            return

        margin = 10.0
        width = self.width() - 2 * margin
        height = self.height() - 2 * margin
        lo, hi = min(self._values), max(self._values)
        span = (hi - lo) or 1.0

        step = width / (len(self._values) - 1)
        points = [
            QPointF(margin + i * step, margin + height - ((value - lo) / span) * height)
            for i, value in enumerate(self._values)
        ]

        pen = QPen(QColor(PALETTE.accent_teal))
        pen.setWidth(2)
        painter.setPen(pen)
        # strict=True specifically segfaults in this PySide6 build when
        # zipping QPointF objects (verified: strict=False is safe). A length
        # mismatch here is structurally impossible anyway — both are slices
        # of the same list.
        for start, end in zip(points, points[1:], strict=False):
            painter.drawLine(start, end)
