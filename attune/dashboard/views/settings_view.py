from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from attune.config.settings import LLMProviderName
from attune.dashboard.viewmodels.settings_view_model import SettingsViewModel
from attune.dashboard.widgets import Card


class SettingsView(QWidget):
    def __init__(self, view_model: SettingsViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        camera_card = Card("Camera")
        camera_form = QFormLayout()
        self._device_index = QSpinBox()
        self._device_index.setRange(0, 10)
        self._fps = QSpinBox()
        self._fps.setRange(1, 60)
        camera_form.addRow("Device index", self._device_index)
        camera_form.addRow("FPS", self._fps)
        camera_card.body_layout.addLayout(camera_form)
        root.addWidget(camera_card)

        llm_card = Card("LLM Provider")
        llm_form = QFormLayout()
        self._provider_combo = QComboBox()
        for provider in LLMProviderName:
            self._provider_combo.addItem(provider.value.title(), provider.value)
        self._model_field = QComboBox()
        self._model_field.setEditable(True)
        llm_form.addRow("Provider", self._provider_combo)
        llm_form.addRow("Model", self._model_field)
        llm_card.body_layout.addLayout(llm_form)
        root.addWidget(llm_card)

        privacy_card = Card("Privacy")
        self._cloud_ai_checkbox = QCheckBox("Allow cloud AI providers (off = local Ollama only)")
        self._debug_frames_checkbox = QCheckBox("Save debug frames to disk")
        privacy_card.body_layout.addWidget(self._cloud_ai_checkbox)
        privacy_card.body_layout.addWidget(self._debug_frames_checkbox)
        root.addWidget(privacy_card)

        performance_card = Card("Performance")
        performance_form = QFormLayout()
        self._confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self._confidence_slider.setRange(0, 100)
        self._confidence_value_label = QLabel("60%")
        self._confidence_slider.valueChanged.connect(
            lambda value: self._confidence_value_label.setText(f"{value}%")
        )
        performance_form.addRow("Confidence threshold", self._confidence_slider)
        performance_form.addRow("", self._confidence_value_label)
        performance_card.body_layout.addLayout(performance_form)
        root.addWidget(performance_card)

        self._save_button = QPushButton("Save Settings")
        self._save_button.setObjectName("PrimaryButton")
        self._save_button.clicked.connect(self._on_save_clicked)
        root.addWidget(self._save_button)

        self._status_label = QLabel("")
        self._status_label.setProperty("role", "secondary")
        root.addWidget(self._status_label)

        root.addStretch(1)

        self._view_model.settings_loaded.connect(self._on_settings_loaded)
        self._view_model.save_succeeded.connect(lambda: self._status_label.setText("Saved."))
        self._view_model.error_occurred.connect(
            lambda message: self._status_label.setText(f"Error: {message}")
        )

    def _on_settings_loaded(self, settings: dict[str, Any]) -> None:
        camera = settings.get("camera", {})
        self._device_index.setValue(camera.get("device_index", 0))
        self._fps.setValue(camera.get("fps", 30))

        llm = settings.get("llm", {})
        provider = llm.get("provider", "ollama")
        index = self._provider_combo.findData(provider)
        if index >= 0:
            self._provider_combo.setCurrentIndex(index)
        self._model_field.setCurrentText(llm.get("model", ""))

        privacy = settings.get("privacy", {})
        self._cloud_ai_checkbox.setChecked(privacy.get("cloud_ai_enabled", False))
        self._debug_frames_checkbox.setChecked(privacy.get("debug_save_frames", False))

        performance = settings.get("performance", {})
        threshold = performance.get("confidence_threshold", 0.6)
        self._confidence_slider.setValue(int(threshold * 100))

    def _on_save_clicked(self) -> None:
        payload = {
            "camera": {
                "device_index": self._device_index.value(),
                "fps": self._fps.value(),
            },
            "llm": {
                "provider": self._provider_combo.currentData(),
                "model": self._model_field.currentText(),
            },
            "privacy": {
                "cloud_ai_enabled": self._cloud_ai_checkbox.isChecked(),
                "debug_save_frames": self._debug_frames_checkbox.isChecked(),
            },
            "performance": {
                "confidence_threshold": self._confidence_slider.value() / 100,
            },
        }
        self._view_model.save(payload)
