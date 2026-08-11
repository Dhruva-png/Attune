from __future__ import annotations

from datetime import date

import pytest
from attune.container import Container
from attune.core.interfaces.repository import IEventRepository, ISessionRepository
from attune.demo.scenarios import AVERAGE_DAY, GREAT_FOCUS_DAY
from attune.demo.seed import seed_demo_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_seed_demo_data_persists_sessions_and_events(api_container: Container) -> None:
    session_repository = api_container.resolve(ISessionRepository)
    event_repository = api_container.resolve(IEventRepository)
    week_plan = (GREAT_FOCUS_DAY, AVERAGE_DAY, None, None, None, None, None)

    result = await seed_demo_data(
        session_repository, event_repository, date(2026, 1, 5), week_plan=week_plan, seed=7
    )

    assert result.session_count == 2

    active_sessions = await session_repository.list_active()
    assert active_sessions == []  # demo sessions are all COMPLETED, not active

    all_events = await event_repository.list(limit=result.event_count)
    assert len(all_events) == result.event_count
