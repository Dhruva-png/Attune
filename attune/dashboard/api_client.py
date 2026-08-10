from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import httpx


class ApiClient:
    """Thin async HTTP client over the local Attune FastAPI backend — the
    dashboard's only path to session/event/analytics data, per
    docs/architecture/03-module-dependencies.md (dashboard never imports
    vision/database/llm directly, only the API).
    """

    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def start_session(self, camera_index: int = 0) -> dict[str, Any]:
        response = await self._client.post(
            "/api/v1/start-session", json={"camera_index": camera_index}
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def end_session(self, session_id: UUID) -> dict[str, Any]:
        response = await self._client.post(
            "/api/v1/end-session", json={"session_id": str(session_id)}
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def get_live_stats(self) -> dict[str, Any] | None:
        response = await self._client.get("/api/v1/live-stats")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def list_events(self, **params: Any) -> dict[str, Any]:
        response = await self._client.get("/api/v1/events", params=params)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def get_daily_report(self, day: date) -> dict[str, Any]:
        response = await self._client.get("/api/v1/reports/daily", params={"date": day.isoformat()})
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def get_weekly_report(self, week_start: date) -> dict[str, Any]:
        response = await self._client.get(
            "/api/v1/reports/weekly", params={"week_start": week_start.isoformat()}
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def get_settings(self) -> dict[str, Any]:
        response = await self._client.get("/api/v1/settings")
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.put("/api/v1/settings", json=payload)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def get_coach_insights(
        self, *, session_id: UUID | None = None, period: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if session_id is not None:
            params["session_id"] = str(session_id)
        if period is not None:
            params["period"] = period
        response = await self._client.get("/api/v1/coach/insights", params=params)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
