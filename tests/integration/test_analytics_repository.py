from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from attune.analytics.engine import AnalyticsEngine
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.entities.session import Session
from attune.core.events.schema import Event, EventType
from attune.database.repositories.analytics_repository import SqlAlchemyAnalyticsRepository
from attune.database.repositories.event_repository import SqlAlchemyEventRepository
from attune.database.repositories.session_repository import SqlAlchemySessionRepository
from attune.database.session import create_engine, create_session_factory, init_models
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest_asyncio.fixture
async def session_factory(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    db_path = tmp_path / "attune_test.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path}")
    await init_models(engine)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analytics_snapshot_round_trips(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlAlchemyAnalyticsRepository(session_factory)
    snapshot = AnalyticsSnapshot(
        period_type=PeriodType.DAILY,
        period_start=date(2026, 1, 5),
        period_end=date(2026, 1, 5),
        avg_focus_score=72.5,
        avg_posture_score=88.0,
        distraction_count=3,
        break_count=2,
        longest_break_seconds=1800,
        best_hours=["09:00-10:00"],
        worst_hours=["15:00-16:00"],
        raw_metrics={"event_count": 42},
    )

    await repo.save(snapshot)
    loaded = await repo.get(PeriodType.DAILY, date(2026, 1, 5))

    assert loaded is not None
    assert loaded.avg_focus_score == 72.5
    assert loaded.best_hours == ["09:00-10:00"]
    assert loaded.raw_metrics == {"event_count": 42}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_saving_the_same_period_overwrites_the_previous_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlAlchemyAnalyticsRepository(session_factory)
    day = date(2026, 1, 5)

    await repo.save(
        AnalyticsSnapshot(
            period_type=PeriodType.DAILY, period_start=day, period_end=day, avg_focus_score=50.0
        )
    )
    await repo.save(
        AnalyticsSnapshot(
            period_type=PeriodType.DAILY, period_start=day, period_end=day, avg_focus_score=90.0
        )
    )

    all_snapshots = await repo.list(PeriodType.DAILY)
    assert len(all_snapshots) == 1
    assert all_snapshots[0].avg_focus_score == 90.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analytics_engine_computes_and_stores_from_real_events(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_repo = SqlAlchemySessionRepository(session_factory)
    event_repo = SqlAlchemyEventRepository(session_factory)
    analytics_repo = SqlAlchemyAnalyticsRepository(session_factory)
    engine = AnalyticsEngine(event_repo, analytics_repo)

    session = Session()
    await session_repo.add(session)

    day = date(2026, 1, 5)
    await event_repo.add(
        Event(
            session_id=session.id,
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime(2026, 1, 5, 9, 0),
            confidence=1.0,
            metadata={"score": 80},
            source_module="test",
        )
    )
    await event_repo.add(
        Event(
            session_id=session.id,
            type=EventType.PHONE_PICKUP,
            timestamp=datetime(2026, 1, 5, 9, 15),
            confidence=0.9,
            source_module="test",
        )
    )

    snapshot = await engine.compute_and_store(PeriodType.DAILY, day, day, session.id)

    assert snapshot.avg_focus_score == 80.0
    assert snapshot.distraction_count == 1

    stored = await analytics_repo.get(PeriodType.DAILY, day, session.id)
    assert stored is not None
    assert stored.avg_focus_score == 80.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_missing_snapshot_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlAlchemyAnalyticsRepository(session_factory)
    assert await repo.get(PeriodType.MONTHLY, date(2026, 1, 1), uuid4()) is None
