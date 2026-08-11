from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from attune.core.interfaces.repository import IEventRepository, ISessionRepository
from attune.demo.generator import generate_week
from attune.demo.scenarios import DEFAULT_WEEK_PLAN, Scenario


@dataclass(frozen=True, slots=True)
class SeedResult:
    session_count: int
    event_count: int


async def seed_demo_data(
    session_repository: ISessionRepository,
    event_repository: IEventRepository,
    start_date: date,
    week_plan: tuple[Scenario | None, ...] = DEFAULT_WEEK_PLAN,
    seed: int | None = None,
) -> SeedResult:
    """Generates a week of synthetic sessions and persists them through the
    same repository ports the real vision/behaviour pipeline writes
    through — demo data is indistinguishable from real data to every layer
    above the repositories, so no other layer needs to know it's synthetic.
    """
    generated_sessions = generate_week(start_date, week_plan=week_plan, seed=seed)

    event_count = 0
    for generated in generated_sessions:
        await session_repository.add(generated.session)
        for event in generated.events:
            await event_repository.add(event)
            event_count += 1

    return SeedResult(session_count=len(generated_sessions), event_count=event_count)
