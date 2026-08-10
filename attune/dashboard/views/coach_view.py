from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from attune.dashboard.viewmodels.coach_view_model import CoachViewModel
from attune.dashboard.widgets import Card


class CoachView(QWidget):
    def __init__(self, view_model: CoachViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header = Card("AI Coach")
        header_label = QLabel(
            "Insights are computed from your actual recorded events — each one "
            "links back to real supporting evidence, never a generic tip."
        )
        header_label.setProperty("role", "secondary")
        header_label.setWordWrap(True)
        header.body_layout.addWidget(header_label)
        root.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("background: transparent; border: none;")
        self._insights_container = QWidget()
        self._insights_layout = QVBoxLayout(self._insights_container)
        self._insights_layout.addStretch(1)
        self._scroll_area.setWidget(self._insights_container)
        root.addWidget(self._scroll_area, stretch=1)

        self._view_model.insights_updated.connect(self._on_insights_updated)

    def _on_insights_updated(self, insights: list[dict[str, Any]]) -> None:
        while self._insights_layout.count() > 1:
            item = self._insights_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        if not insights:
            empty_card = Card()
            empty_label = QLabel(
                "No patterns detected yet — insights appear once enough data has "
                "been collected across your sessions."
            )
            empty_label.setProperty("role", "secondary")
            empty_label.setWordWrap(True)
            empty_card.body_layout.addWidget(empty_label)
            self._insights_layout.insertWidget(0, empty_card)
            return

        for insight in insights:
            card = Card()
            text_label = QLabel(insight["text"])
            text_label.setWordWrap(True)
            card.body_layout.addWidget(text_label)

            evidence_count = len(insight["evidence_event_ids"])
            confidence_label = QLabel(
                f"confidence {insight['confidence']:.0%} · {evidence_count} supporting events"
            )
            confidence_label.setProperty("role", "muted")
            card.body_layout.addWidget(confidence_label)

            self._insights_layout.insertWidget(self._insights_layout.count() - 1, card)
