from __future__ import annotations

import asyncio
from typing import Any

import httpx
from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient


class SettingsViewModel(QObject):
    """Load-once / save-on-demand — settings don't need periodic polling."""

    settings_loaded = Signal(dict)
    save_succeeded = Signal()
    error_occurred = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client

    def load(self) -> None:
        asyncio.ensure_future(self._load_async())

    async def _load_async(self) -> None:
        try:
            settings = await self._api_client.get_settings()
        except httpx.HTTPError as exc:
            self.error_occurred.emit(str(exc))
            return
        self.settings_loaded.emit(settings)

    def save(self, payload: dict[str, Any]) -> None:
        asyncio.ensure_future(self._save_async(payload))

    async def _save_async(self, payload: dict[str, Any]) -> None:
        try:
            settings = await self._api_client.update_settings(payload)
        except httpx.HTTPError as exc:
            self.error_occurred.emit(str(exc))
            return
        self.settings_loaded.emit(settings)
        self.save_succeeded.emit()
