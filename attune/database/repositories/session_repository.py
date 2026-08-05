from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from attune.core.entities.fatigue import FatigueLevel
from attune.core.entities.session import Session, SessionStatus
from attune.database.models import SessionModel


def _to_domain(row: SessionModel) -> Session:
    return Session(
        id=uuid.UUID(row.id),
        started_at=row.started_at,
        ended_at=row.ended_at,
        status=SessionStatus(row.status),
        focus_score_avg=row.focus_score_avg,
        posture_score_avg=row.posture_score_avg,
        fatigue_level_end=FatigueLevel(row.fatigue_level_end) if row.fatigue_level_end else None,
    )


def _to_row(session: Session) -> SessionModel:
    return SessionModel(
        id=str(session.id),
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status.value,
        focus_score_avg=session.focus_score_avg,
        posture_score_avg=session.posture_score_avg,
        fatigue_level_end=session.fatigue_level_end.value if session.fatigue_level_end else None,
    )


class SqlAlchemySessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, session: Session) -> None:
        async with self._session_factory() as db_session, db_session.begin():
            db_session.add(_to_row(session))

    async def get(self, session_id: uuid.UUID) -> Session | None:
        async with self._session_factory() as db_session:
            row = await db_session.get(SessionModel, str(session_id))
            return _to_domain(row) if row is not None else None

    async def update(self, session: Session) -> None:
        async with self._session_factory() as db_session, db_session.begin():
            row = await db_session.get(SessionModel, str(session.id))
            if row is None:
                raise LookupError(f"no session with id {session.id}")
            row.ended_at = session.ended_at
            row.status = session.status.value
            row.focus_score_avg = session.focus_score_avg
            row.posture_score_avg = session.posture_score_avg
            row.fatigue_level_end = (
                session.fatigue_level_end.value if session.fatigue_level_end else None
            )

    async def list_active(self) -> list[Session]:
        async with self._session_factory() as db_session:
            result = await db_session.execute(
                select(SessionModel).where(SessionModel.status == SessionStatus.ACTIVE.value)
            )
            return [_to_domain(row) for row in result.scalars().all()]
