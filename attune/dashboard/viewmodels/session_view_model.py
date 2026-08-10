from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import httpx
from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient


class SessionViewModel(QObject):
    """Owns session start/end for the nav rail's timer + status pill."""

    session_started = Signal(dict)
    session_ended = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client
        self.active_session: dict[str, Any] | None = None

    def start_session(self, camera_index: int = 0) -> None:
        asyncio.ensure_future(self._start_async(camera_index))

    async def _start_async(self, camera_index: int) -> None:
        try:
            session = await self._api_client.start_session(camera_index)
        except httpx.HTTPError as exc:
            self.error_occurred.emit(str(exc))
            return
        self.active_session = session
        self.session_started.emit(session)

    def end_session(self) -> None:
        if self.active_session is not None:
            asyncio.ensure_future(self._end_async(self.active_session["session_id"]))

    async def _end_async(self, session_id: str) -> None:
        try:
            session = await self._api_client.end_session(UUID(session_id))
        except httpx.HTTPError as exc:
            self.error_occurred.emit(str(exc))
            return
        self.active_session = None
        self.session_ended.emit(session)
