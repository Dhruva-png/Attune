from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from attune.dashboard.theme.tokens import PALETTE

_TRACK_COLOR = QColor(255, 255, 255, 25)
_RING_WIDTH = 10


class FocusGauge(QWidget):
    """A circular 0-100 progress ring for the live focus score."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: float | None = None
        self.setMinimumSize(130, 130)

    def set_value(self, value: float | None) -> None:
        self._value = value
        self.update()

    @staticmethod
    def _ring_color(value: float) -> QColor:
        if value >= 70:
            return QColor(PALETTE.good)
        if value >= 40:
            return QColor(PALETTE.caution)
        return QColor(PALETTE.alert)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height()) - _RING_WIDTH - 4
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        track_pen = QPen(_TRACK_COLOR)
        track_pen.setWidth(_RING_WIDTH)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self._value is not None:
            value_pen = QPen(self._ring_color(self._value))
            value_pen.setWidth(_RING_WIDTH)
            value_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(value_pen)
            span = int(360 * 16 * (self._value / 100))
            painter.drawArc(rect, 90 * 16, -span)

        painter.setPen(QColor(PALETTE.text_primary))
        font = painter.font()
        font.setPointSize(22)
        font.setBold(True)
        painter.setFont(font)
        text = f"{int(self._value)}" if self._value is not None else "--"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
