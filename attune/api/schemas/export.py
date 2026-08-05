from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ExportScope(StrEnum):
    SESSION = "session"
    DAILY = "daily"
    WEEKLY = "weekly"


class ExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


class ExportRequest(BaseModel):
    scope: ExportScope
    target_id: str  # session UUID for scope=session, ISO date otherwise
    format: ExportFormat
