from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from attune.core.entities.session import Session, SessionStatus
from attune.core.events.bus import EventBus
from attune.core.events.schema import Event, EventType
from attune.database.event_logger import EventLogger
from attune.database.repositories.event_repository import SqlAlchemyEventRepository
from attune.database.repositories.session_repository import SqlAlchemySessionRepository
from attune.database.repositories.settings_repository import SqlAlchemySettingsStore
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
async def test_session_and_events_round_trip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_repo = SqlAlchemySessionRepository(session_factory)
    event_repo = SqlAlchemyEventRepository(session_factory)

    session = Session()
    await session_repo.add(session)

    events = [
        Event(
            session_id=session.id,
            type=EventType.SESSION_STARTED,
            confidence=1.0,
            source_module="test",
        ),
        Event(
            session_id=session.id,
            type=EventType.POOR_POSTURE,
            confidence=0.9,
            metadata={"neck_angle_deg": 30.0},
            source_module="test",
        ),
        Event(
            session_id=session.id,
            type=EventType.PHONE_PICKUP,
            confidence=0.8,
            source_module="test",
        ),
    ]
    for event in events:
        await event_repo.add(event)

    loaded_session = await session_repo.get(session.id)
    assert loaded_session is not None
    assert loaded_session.id == session.id
    assert loaded_session.status == SessionStatus.ACTIVE

    loaded_events = await event_repo.list(session_id=session.id)
    assert len(loaded_events) == 3
    assert {e.type for e in loaded_events} == {
        EventType.SESSION_STARTED,
        EventType.POOR_POSTURE,
        EventType.PHONE_PICKUP,
    }
    poor_posture = next(e for e in loaded_events if e.type == EventType.POOR_POSTURE)
    assert poor_posture.metadata["neck_angle_deg"] == 30.0
    assert poor_posture.confidence == 0.9


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_filtering_by_type_and_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_repo = SqlAlchemySessionRepository(session_factory)
    event_repo = SqlAlchemyEventRepository(session_factory)

    session_a, session_b = Session(), Session()
    await session_repo.add(session_a)
    await session_repo.add(session_b)

    await event_repo.add(
        Event(session_id=session_a.id, type=EventType.YAWN, confidence=0.9, source_module="test")
    )
    await event_repo.add(
        Event(
            session_id=session_a.id,
            type=EventType.GOOD_POSTURE,
            confidence=0.9,
            source_module="test",
        )
    )
    await event_repo.add(
        Event(session_id=session_b.id, type=EventType.YAWN, confidence=0.9, source_module="test")
    )

    session_a_events = await event_repo.list(session_id=session_a.id)
    assert len(session_a_events) == 2

    yawns_only = await event_repo.list(event_type=EventType.YAWN)
    assert len(yawns_only) == 2
    assert all(e.type == EventType.YAWN for e in yawns_only)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_update_reflects_in_list_active(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_repo = SqlAlchemySessionRepository(session_factory)

    session = Session()
    await session_repo.add(session)
    assert session.id in [s.id for s in await session_repo.list_active()]

    session.end()
    await session_repo.update(session)

    active = await session_repo.list_active()
    assert session.id not in [s.id for s in active]

    reloaded = await session_repo.get(session.id)
    assert reloaded is not None
    assert reloaded.status == SessionStatus.COMPLETED
    assert reloaded.ended_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_settings_store_round_trip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SqlAlchemySettingsStore(session_factory)

    await store.save({"theme": "light", "camera": {"device_index": 1}})
    values = await store.load()

    assert values["theme"] == "light"
    assert values["camera"] == {"device_index": 1}
    assert values["llm"] == {}  # untouched fields keep their default

    await store.save({"theme": "dark"})
    values = await store.load()
    assert values["theme"] == "dark"
    assert values["camera"] == {"device_index": 1}  # previous save preserved


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_bus_publish_persists_via_event_logger(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    event_repo = SqlAlchemyEventRepository(session_factory)
    session_repo = SqlAlchemySessionRepository(session_factory)
    bus = EventBus()
    bus.subscribe_all(EventLogger(event_repo).handle)

    session = Session()
    await session_repo.add(session)

    await bus.publish(
        Event(
            session_id=session.id,
            type=EventType.LEFT_DESK,
            confidence=0.95,
            source_module="behaviour.breaks",
        )
    )

    stored = await event_repo.list(session_id=session.id)
    assert len(stored) == 1
    assert stored[0].type == EventType.LEFT_DESK


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_missing_session_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_repo = SqlAlchemySessionRepository(session_factory)
    assert await session_repo.get(uuid.uuid4()) is None
