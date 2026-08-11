#!/usr/bin/env python
"""Populates the configured database with a week of synthetic, realistic
session data — no webcam required. Useful for trying out the dashboard,
taking screenshots, or exercising the API/analytics against non-trivial
data.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --start-date 2026-01-05 --seed 42
    python scripts/seed_demo_data.py --reset   # wipes existing tables first
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from attune.bootstrap import bootstrap
from attune.config.settings import get_settings
from attune.core.interfaces.repository import IEventRepository, ISessionRepository
from attune.database.models import Base
from attune.database.session import init_models
from attune.demo.seed import seed_demo_data
from sqlalchemy.ext.asyncio import AsyncEngine


def _this_weeks_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        help="ISO date the synthetic week starts on (default: this week's Monday)",
    )
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible output")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before seeding (destructive)",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    start_date = args.start_date or _this_weeks_monday()

    settings = get_settings()
    container = bootstrap(settings)
    engine = container.resolve(AsyncEngine)

    if args.reset:
        print(f"--reset: dropping and recreating all tables in {settings.database_url}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await init_models(engine)

    session_repository = container.resolve(ISessionRepository)
    event_repository = container.resolve(IEventRepository)

    result = await seed_demo_data(session_repository, event_repository, start_date, seed=args.seed)

    print(
        f"Seeded {result.session_count} session(s) / {result.event_count} event(s) "
        f"starting {start_date.isoformat()} into {settings.database_url}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
