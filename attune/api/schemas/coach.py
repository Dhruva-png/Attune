from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CoachInsightResponse(BaseModel):
    text: str
    confidence: float
    evidence_event_ids: list[UUID]


class CoachInsightsResponse(BaseModel):
    insights: list[CoachInsightResponse]
    generated_by: str
    generated_at: datetime
