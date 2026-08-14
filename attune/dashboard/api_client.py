from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import httpx

# LLM-backed and can take much longer than a snappy local DB call — a cold
# Ollama model load alone has been observed at 25s+, well past the client's
# default request timeout, so this endpoint gets its own generous budget.
COACH_INSIGHTS_TIMEOUT_SECONDS = 90.0


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

    async def get_live_frame(self) -> bytes | None:
        response = await self._client.get("/api/v1/live-stats/frame")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.content

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
        response = await self._client.get(
            "/api/v1/coach/insights", params=params, timeout=COACH_INSIGHTS_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def export(self, *, scope: str, target_id: str, export_format: str) -> httpx.Response:
        """Returns the raw response — sync formats (json/csv) come back as a
        200 with the file body attached; pdf/png come back as a 202 job
        descriptor to poll via get_report_status/download_report.
        """
        response = await self._client.post(
            "/api/v1/export",
            json={"scope": scope, "target_id": target_id, "format": export_format},
        )
        response.raise_for_status()
        return response

    async def get_report_status(self, report_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/api/v1/reports/{report_id}")
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def download_report(self, report_id: str) -> httpx.Response:
        response = await self._client.get(f"/api/v1/reports/{report_id}/download")
        response.raise_for_status()
        return response
