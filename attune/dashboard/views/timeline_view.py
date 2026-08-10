from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from attune.dashboard.viewmodels.timeline_view_model import TimelineViewModel
from attune.dashboard.widgets import Card


class TimelineView(QWidget):
    def __init__(self, view_model: TimelineViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        card = Card("Timeline")
        self._list = QListWidget()
        card.body_layout.addWidget(self._list)
        root.addWidget(card)

        self._view_model.events_updated.connect(self.set_events)

    def set_events(self, events: list[dict[str, Any]]) -> None:
        self._list.clear()
        for event in reversed(events):
            time_str = event["timestamp"][11:16]
            label = event["type"].replace("_", " ").title()
            confidence = event.get("confidence", 0.0)
            self._list.addItem(f"{time_str}   {label}   (confidence {confidence:.2f})")
