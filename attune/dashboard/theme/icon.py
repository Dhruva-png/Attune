from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from attune.dashboard.theme.tokens import PALETTE

# No dedicated logo asset exists yet (attune/assets/ is still empty) — a
# rendered emoji on a branded rounded-square background is a reasonable
# stand-in that at least makes the window/taskbar icon identifiable instead
# of falling back to Qt's generic default.
_EMOJI = "\U0001f3af"  # 🎯


def app_icon(size: int = 256) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(PALETTE.accent_indigo))
    radius = size * 0.22
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    font = QFont("Segoe UI Emoji")
    font.setPixelSize(int(size * 0.58))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, _EMOJI)
    painter.end()

    return QIcon(pixmap)
