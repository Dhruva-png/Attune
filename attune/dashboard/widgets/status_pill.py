from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from attune.dashboard.theme.tokens import PALETTE

_STATUS_COLORS = {
    "focused": PALETTE.good,
    "distracted": PALETTE.caution,
    "away": PALETTE.alert,
    "good": PALETTE.good,
    "poor": PALETTE.alert,
    "unknown": PALETTE.text_muted,
    "active": PALETTE.good,
    "completed": PALETTE.text_secondary,
}


class StatusPill(QLabel):
    """A small colored-dot status indicator (docs/architecture/07-ui-wireframes.md)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.set_status("unknown")

    def set_status(self, status: str, text: str | None = None) -> None:
        color = _STATUS_COLORS.get(status, PALETTE.text_muted)
        label = text or status.replace("_", " ").title()
        self.setText(f"● {label}")
        self.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
