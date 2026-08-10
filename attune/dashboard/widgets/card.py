from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    """A rounded glass panel — the base visual unit of every dashboard view."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(16, 14, 16, 14)
        self.body_layout.setSpacing(6)

        if title:
            title_label = QLabel(title)
            title_label.setProperty("role", "title")
            self.body_layout.addWidget(title_label)
