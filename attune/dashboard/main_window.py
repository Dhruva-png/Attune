from __future__ import annotations

from typing import Any

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels import (
    AnalyticsViewModel,
    CoachViewModel,
    ExportViewModel,
    LiveViewModel,
    SessionViewModel,
    SettingsViewModel,
    TimelineViewModel,
)
from attune.dashboard.views import AnalyticsView, CoachView, LiveView, SettingsView, TimelineView
from attune.dashboard.widgets import StatusPill

NAV_ITEMS = [
    "⌂  Live",
    "◷  Timeline",
    "▤  Analytics",
    "✦  AI Coach",
    "⚙  Settings",
]


class MainWindow(QWidget):
    """The app shell: nav rail + stacked view area, per
    docs/architecture/07-ui-wireframes.md.
    """

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RootWindow")
        self.setWindowTitle("Attune")
        self.resize(1280, 800)
        self._center_on_screen()

        self._session_view_model = SessionViewModel(api_client, self)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._nav_buttons: list[QPushButton] = []
        root_layout.addWidget(self._build_nav_rail())

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, stretch=1)

        self._live_view_model = LiveViewModel(api_client, self)
        self._timeline_view_model = TimelineViewModel(api_client, self)
        self._analytics_view_model = AnalyticsViewModel(api_client, self)
        self._coach_view_model = CoachViewModel(api_client, self)
        self._settings_view_model = SettingsViewModel(api_client, self)
        self._export_view_model = ExportViewModel(api_client, self)

        self._live_view = LiveView(self._live_view_model)
        for view in (
            self._live_view,
            TimelineView(self._timeline_view_model),
            AnalyticsView(self._analytics_view_model, self._export_view_model),
            CoachView(self._coach_view_model),
            SettingsView(self._settings_view_model),
        ):
            self._stack.addWidget(view)

        # The Live view's event feed reuses the Timeline poll rather than
        # adding a second, redundant /events cadence.
        self._timeline_view_model.events_updated.connect(self._live_view.set_events)

        self._session_view_model.session_started.connect(self._on_session_started)
        self._session_view_model.session_ended.connect(self._on_session_ended)
        self._session_view_model.error_occurred.connect(self._on_session_error)

        self._live_view_model.start()
        self._timeline_view_model.start()
        self._analytics_view_model.start()
        self._coach_view_model.start()
        self._settings_view_model.load()

        self._nav_buttons[0].setChecked(True)

    def _center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def _build_nav_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("NavRail")
        rail.setFixedWidth(200)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        brand = QLabel("Attune")
        brand.setProperty("role", "title")
        layout.addWidget(brand)
        layout.addSpacing(20)

        button_group = QButtonGroup(rail)
        button_group.setExclusive(True)

        for index, label in enumerate(NAV_ITEMS):
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self._stack.setCurrentIndex(i))
            layout.addWidget(button)
            button_group.addButton(button)
            self._nav_buttons.append(button)

        layout.addStretch(1)

        self._session_status_pill = StatusPill()
        self._session_status_pill.set_status("unknown", "No session")
        layout.addWidget(self._session_status_pill)

        self._session_button = QPushButton("Start Session")
        self._session_button.setObjectName("PrimaryButton")
        self._session_button.clicked.connect(self._on_session_button_clicked)
        layout.addWidget(self._session_button)

        return rail

    def _on_session_button_clicked(self) -> None:
        if self._session_view_model.active_session is None:
            self._session_view_model.start_session()
        else:
            self._session_view_model.end_session()

    def _on_session_started(self, session: dict[str, Any]) -> None:
        self._session_status_pill.set_status("active", "Session active")
        self._session_button.setText("End Session")

    def _on_session_ended(self, session: dict[str, Any]) -> None:
        self._session_status_pill.set_status("unknown", "No session")
        self._session_button.setText("Start Session")

    def _on_session_error(self, message: str) -> None:
        self._session_status_pill.set_status("unknown", "Error")
