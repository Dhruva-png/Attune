from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from attune.dashboard.viewmodels.analytics_view_model import AnalyticsViewModel
from attune.dashboard.widgets import Card, TrendChart


class AnalyticsView(QWidget):
    def __init__(self, view_model: AnalyticsViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        focus_card = Card("Avg Focus Score (Today)")
        self._focus_label = QLabel("--")
        self._focus_label.setProperty("role", "metric")
        focus_card.body_layout.addWidget(self._focus_label)

        posture_card = Card("Avg Posture Score (Today)")
        self._posture_label = QLabel("--")
        self._posture_label.setProperty("role", "metric")
        posture_card.body_layout.addWidget(self._posture_label)

        distraction_card = Card("Distractions (Today)")
        self._distraction_label = QLabel("--")
        self._distraction_label.setProperty("role", "metric")
        distraction_card.body_layout.addWidget(self._distraction_label)

        breaks_card = Card("Breaks (Today)")
        self._breaks_label = QLabel("--")
        self._breaks_label.setProperty("role", "metric")
        breaks_card.body_layout.addWidget(self._breaks_label)

        for column, card in enumerate((focus_card, posture_card, distraction_card, breaks_card)):
            grid.addWidget(card, 0, column)
        root.addLayout(grid)

        trend_card = Card("Weekly Focus Trend")
        self._trend_chart = TrendChart()
        trend_card.body_layout.addWidget(self._trend_chart)
        root.addWidget(trend_card)

        hours_card = Card("Best / Worst Hours (This Week)")
        self._hours_label = QLabel("--")
        self._hours_label.setProperty("role", "secondary")
        self._hours_label.setWordWrap(True)
        hours_card.body_layout.addWidget(self._hours_label)
        root.addWidget(hours_card)

        root.addStretch(1)

        self._view_model.daily_updated.connect(self._on_daily_updated)
        self._view_model.weekly_updated.connect(self._on_weekly_updated)

    def _on_daily_updated(self, report: dict[str, Any]) -> None:
        focus = report.get("avg_focus_score")
        self._focus_label.setText(f"{focus:.0f}" if focus is not None else "--")

        posture = report.get("avg_posture_score")
        self._posture_label.setText(f"{posture:.0f}%" if posture is not None else "--")

        self._distraction_label.setText(str(report.get("distraction_count", 0)))
        self._breaks_label.setText(str(report.get("break_count", 0)))

    def _on_weekly_updated(self, report: dict[str, Any]) -> None:
        daily_breakdown = report.get("daily_breakdown", [])
        scores = [
            day["avg_focus_score"]
            for day in daily_breakdown
            if day.get("avg_focus_score") is not None
        ]
        self._trend_chart.set_values(scores)

        best = ", ".join(report.get("best_hours", [])) or "not enough data yet"
        worst = ", ".join(report.get("worst_hours", [])) or "not enough data yet"
        self._hours_label.setText(f"Best: {best}\nWorst: {worst}")
