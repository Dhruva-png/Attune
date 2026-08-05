from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.database.models import AnalyticsSnapshotModel


def _to_domain(row: AnalyticsSnapshotModel) -> AnalyticsSnapshot:
    return AnalyticsSnapshot(
        id=uuid.UUID(row.id),
        session_id=uuid.UUID(row.session_id) if row.session_id else None,
        period_type=PeriodType(row.period_type),
        period_start=row.period_start,
        period_end=row.period_end,
        avg_focus_score=row.avg_focus_score,
        avg_posture_score=row.avg_posture_score,
        distraction_count=row.distraction_count,
        break_count=row.break_count,
        longest_break_seconds=row.longest_break_seconds,
        best_hours=list(row.best_hours),
        worst_hours=list(row.worst_hours),
        raw_metrics=dict(row.raw_metrics),
        computed_at=row.computed_at,
    )


def _to_row(snapshot: AnalyticsSnapshot) -> AnalyticsSnapshotModel:
    return AnalyticsSnapshotModel(
        id=str(snapshot.id),
        session_id=str(snapshot.session_id) if snapshot.session_id else None,
        period_type=snapshot.period_type.value,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        avg_focus_score=snapshot.avg_focus_score,
        avg_posture_score=snapshot.avg_posture_score,
        distraction_count=snapshot.distraction_count,
        break_count=snapshot.break_count,
        longest_break_seconds=snapshot.longest_break_seconds,
        best_hours=list(snapshot.best_hours),
        worst_hours=list(snapshot.worst_hours),
        raw_metrics=dict(snapshot.raw_metrics),
    )


class SqlAlchemyAnalyticsRepository:
    """IAnalyticsRepository implementation over the `analytics_snapshots`
    table — cached rollups, always rebuildable from `events`
    (docs/architecture/04-database-schema.md design notes).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, snapshot: AnalyticsSnapshot) -> None:
        async with self._session_factory() as session, session.begin():
            existing = await session.execute(
                select(AnalyticsSnapshotModel).where(
                    AnalyticsSnapshotModel.period_type == snapshot.period_type.value,
                    AnalyticsSnapshotModel.period_start == snapshot.period_start,
                    AnalyticsSnapshotModel.session_id
                    == (str(snapshot.session_id) if snapshot.session_id else None),
                )
            )
            row = existing.scalar_one_or_none()
            if row is not None:
                await session.delete(row)
                await session.flush()
            session.add(_to_row(snapshot))

    async def get(
        self, period_type: PeriodType, period_start: date, session_id: uuid.UUID | None = None
    ) -> AnalyticsSnapshot | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AnalyticsSnapshotModel).where(
                    AnalyticsSnapshotModel.period_type == period_type.value,
                    AnalyticsSnapshotModel.period_start == period_start,
                    AnalyticsSnapshotModel.session_id == (str(session_id) if session_id else None),
                )
            )
            row = result.scalar_one_or_none()
            return _to_domain(row) if row is not None else None

    async def list(
        self, period_type: PeriodType, session_id: uuid.UUID | None = None
    ) -> list[AnalyticsSnapshot]:
        async with self._session_factory() as session:
            stmt = select(AnalyticsSnapshotModel).where(
                AnalyticsSnapshotModel.period_type == period_type.value
            )
            if session_id is not None:
                stmt = stmt.where(AnalyticsSnapshotModel.session_id == str(session_id))
            stmt = stmt.order_by(AnalyticsSnapshotModel.period_start)

            result = await session.execute(stmt)
            return [_to_domain(row) for row in result.scalars().all()]
