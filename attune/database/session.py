from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from attune.database.models import Base


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Dev/test convenience: creates tables directly from the ORM metadata.

    Production schema changes go through Alembic (attune/database/migrations/)
    so they're versioned and reviewable; this is for fast, isolated test setup
    where running a full migration chain would be unnecessary overhead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
