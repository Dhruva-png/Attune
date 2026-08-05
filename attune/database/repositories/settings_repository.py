from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from attune.database.models import SettingsModel

SETTINGS_ROW_ID = 1
SETTINGS_FIELDS = ("camera", "llm", "privacy", "notifications", "performance", "theme")


class SqlAlchemySettingsStore:
    """ISettingsStore implementation over the single-row `settings` table."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self) -> dict[str, object]:
        async with self._session_factory() as session:
            row = await session.get(SettingsModel, SETTINGS_ROW_ID)
            if row is None:
                return {}
            return {field: getattr(row, field) for field in SETTINGS_FIELDS}

    async def save(self, values: dict[str, object]) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(SettingsModel, SETTINGS_ROW_ID)
            if row is None:
                row = SettingsModel(id=SETTINGS_ROW_ID)
                session.add(row)
            for field in SETTINGS_FIELDS:
                if field in values:
                    setattr(row, field, values[field])
