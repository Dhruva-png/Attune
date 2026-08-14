from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QListWidget, QVBoxLayout, QWidget

from attune.dashboard.viewmodels.live_view_model import LiveViewModel
from attune.dashboard.widgets import Card, FocusGauge, StatusPill

MAX_LIVE_EVENTS_SHOWN = 10
CAMERA_PREVIEW_MIN_HEIGHT = 240
NO_SESSION_MESSAGE = "No active session — camera preview appears once a session starts."


class LiveView(QWidget):
    def __init__(self, view_model: LiveViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        top_row = QGridLayout()
        top_row.setSpacing(16)

        camera_card = Card("Camera Preview")
        self._camera_label = QLabel(NO_SESSION_MESSAGE)
        self._camera_label.setProperty("role", "secondary")
        self._camera_label.setWordWrap(True)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setMinimumHeight(CAMERA_PREVIEW_MIN_HEIGHT)
        camera_card.body_layout.addWidget(self._camera_label)

        focus_card = Card("Focus Score")
        self._gauge = FocusGauge()
        focus_card.body_layout.addWidget(self._gauge, alignment=Qt.AlignmentFlag.AlignHCenter)

        status_card = Card("Status")
        self._status_pill = StatusPill()
        self._elapsed_label = QLabel("--")
        self._elapsed_label.setProperty("role", "secondary")
        status_card.body_layout.addWidget(self._status_pill)
        status_card.body_layout.addWidget(self._elapsed_label)

        top_row.addWidget(camera_card, 0, 0, 2, 1)
        top_row.addWidget(focus_card, 0, 1)
        top_row.addWidget(status_card, 1, 1)
        top_row.setColumnStretch(0, 2)
        top_row.setColumnStretch(1, 1)
        root.addLayout(top_row)

        metrics_row = QGridLayout()
        metrics_row.setSpacing(16)

        fatigue_card = Card("Fatigue")
        self._fatigue_label = QLabel("--")
        self._fatigue_label.setProperty("role", "metric")
        fatigue_card.body_layout.addWidget(self._fatigue_label)

        posture_card = Card("Posture")
        self._posture_pill = StatusPill()
        posture_card.body_layout.addWidget(self._posture_pill)

        phone_card = Card("Phone Activity")
        self._phone_label = QLabel("--")
        self._phone_label.setProperty("role", "metric")
        phone_card.body_layout.addWidget(self._phone_label)

        breaks_card = Card("Breaks")
        self._breaks_label = QLabel("--")
        self._breaks_label.setProperty("role", "metric")
        breaks_card.body_layout.addWidget(self._breaks_label)

        for column, card in enumerate((fatigue_card, posture_card, phone_card, breaks_card)):
            metrics_row.addWidget(card, 0, column)
        root.addLayout(metrics_row)

        events_card = Card("Live Events")
        self._events_list = QListWidget()
        self._events_list.setMaximumHeight(180)
        events_card.body_layout.addWidget(self._events_list)
        root.addWidget(events_card, stretch=1)

        self._view_model.stats_updated.connect(self._on_stats_updated)
        self._view_model.stats_unavailable.connect(self._on_stats_unavailable)
        self._view_model.frame_updated.connect(self._on_frame_updated)
        self._view_model.frame_unavailable.connect(self._on_frame_unavailable)

    def _on_stats_updated(self, stats: dict[str, Any]) -> None:
        self._gauge.set_value(stats.get("focus_score"))
        self._status_pill.set_status(stats.get("status", "unknown"))
        elapsed = stats.get("elapsed_seconds", 0)
        self._elapsed_label.setText(f"{int(elapsed // 60)}m {int(elapsed % 60)}s elapsed")
        fatigue = stats.get("fatigue_level") or "unknown"
        self._fatigue_label.setText(fatigue.replace("_", " ").title())
        self._posture_pill.set_status(stats.get("posture", "unknown"))

        phone = stats.get("phone_activity") or {}
        self._phone_label.setText(f"{phone.get('interactions_today', 0)} today")

        breaks = stats.get("breaks") or {}
        total_minutes = int(breaks.get("total_seconds", 0) // 60)
        self._breaks_label.setText(f"{breaks.get('count', 0)} · {total_minutes}m total")

    def _on_stats_unavailable(self) -> None:
        self._gauge.set_value(None)
        self._status_pill.set_status("unknown", "No active session")
        self._elapsed_label.setText("--")
        self._fatigue_label.setText("--")
        self._posture_pill.set_status("unknown")
        self._phone_label.setText("--")
        self._breaks_label.setText("--")
        self._on_frame_unavailable()

    def _on_frame_updated(self, jpeg_bytes: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(jpeg_bytes, b"JPG"):
            return
        self._camera_label.setPixmap(
            pixmap.scaledToHeight(
                CAMERA_PREVIEW_MIN_HEIGHT, Qt.TransformationMode.SmoothTransformation
            )
        )

    def _on_frame_unavailable(self) -> None:
        self._camera_label.setPixmap(QPixmap())
        self._camera_label.setText(NO_SESSION_MESSAGE)

    def set_events(self, events: list[dict[str, Any]]) -> None:
        self._events_list.clear()
        for event in reversed(events[-MAX_LIVE_EVENTS_SHOWN:]):
            time_str = event["timestamp"][11:16]
            label = event["type"].replace("_", " ").title()
            self._events_list.addItem(f"{time_str}   {label}")
