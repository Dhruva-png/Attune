from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from attune.dashboard.viewmodels.analytics_view_model import AnalyticsViewModel
from attune.dashboard.viewmodels.export_view_model import ExportViewModel
from attune.dashboard.widgets import Card, TrendChart


class AnalyticsView(QWidget):
    def __init__(
        self,
        view_model: AnalyticsViewModel,
        export_view_model: ExportViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model
        self._export_view_model = export_view_model
        self._week_start: str | None = None

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

        export_card = Card("Export")
        export_row = QHBoxLayout()
        self._export_button = QPushButton("Export Weekly Report (PDF)")
        self._export_button.clicked.connect(self._on_export_clicked)
        export_row.addWidget(self._export_button)
        self._export_status_label = QLabel("")
        self._export_status_label.setProperty("role", "secondary")
        export_row.addWidget(self._export_status_label, stretch=1)
        export_card.body_layout.addLayout(export_row)
        root.addWidget(export_card)

        root.addStretch(1)

        self._view_model.daily_updated.connect(self._on_daily_updated)
        self._view_model.weekly_updated.connect(self._on_weekly_updated)
        self._export_view_model.export_started.connect(self._on_export_started)
        self._export_view_model.export_ready.connect(self._on_export_ready)
        self._export_view_model.export_failed.connect(self._on_export_failed)

    def _on_daily_updated(self, report: dict[str, Any]) -> None:
        focus = report.get("avg_focus_score")
        self._focus_label.setText(f"{focus:.0f}" if focus is not None else "--")

        posture = report.get("avg_posture_score")
        self._posture_label.setText(f"{posture:.0f}%" if posture is not None else "--")

        self._distraction_label.setText(str(report.get("distraction_count", 0)))
        self._breaks_label.setText(str(report.get("break_count", 0)))

    def _on_weekly_updated(self, report: dict[str, Any]) -> None:
        self._week_start = report.get("week_start")

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

    def _on_export_clicked(self) -> None:
        if self._week_start is None:
            return
        self._export_view_model.export(
            scope="weekly", target_id=self._week_start, export_format="pdf"
        )

    def _on_export_started(self) -> None:
        self._export_button.setEnabled(False)
        self._export_status_label.setText("Generating report…")

    def _on_export_ready(self, content: bytes, suggested_filename: str) -> None:
        self._export_button.setEnabled(True)
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", suggested_filename)
        if not path:
            self._export_status_label.setText("Export ready (not saved)")
            return
        Path(path).write_bytes(content)
        self._export_status_label.setText(f"Saved to {path}")

    def _on_export_failed(self, message: str) -> None:
        self._export_button.setEnabled(True)
        self._export_status_label.setText(f"Export failed: {message}")
