#!/usr/bin/env python
"""Seeds a throwaway demo database with a realistic week of data, launches
the dashboard against it, and screenshots every view into docs/screenshots/
— the source of the README/marketing screenshots. Doesn't touch the app's
real configured database.

Usage:
    python scripts/generate_marketing_assets.py [--seed 42]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import qasync
import uvicorn
from PySide6.QtWidgets import QApplication

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from attune.api.main import create_app as create_api_app  # noqa: E402
from attune.bootstrap import bootstrap  # noqa: E402
from attune.config.settings import Settings  # noqa: E402
from attune.container import Container  # noqa: E402
from attune.core.interfaces.repository import (  # noqa: E402
    IEventRepository,
    ISessionRepository,
)
from attune.dashboard.api_client import ApiClient  # noqa: E402
from attune.dashboard.main_window import MainWindow  # noqa: E402
from attune.dashboard.theme import build_stylesheet  # noqa: E402
from attune.database.session import init_models  # noqa: E402
from attune.demo.seed import seed_demo_data  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots"
NAV_LABELS = ["live", "timeline", "analytics", "coach", "settings"]
DEMO_PORT = 8499


async def _serve_api(container: Container, host: str, port: int, ready: asyncio.Event) -> None:
    api_app = create_api_app(container=container)
    config = uvicorn.Config(api_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    serve_task = asyncio.ensure_future(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    ready.set()
    await serve_task


async def _tour(window: MainWindow, qt_app: QApplication) -> None:
    await asyncio.sleep(1.0)  # let the first poll cycle land
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(NAV_LABELS):
        window._nav_buttons[index].click()
        # The Coach view's insights come from a real local LLM call (started
        # at window-construction time, not on tab visit) — a few hundred ms
        # is nowhere near enough for that to finish, so give it real time.
        await asyncio.sleep(20.0 if name == "coach" else 0.5)
        out_path = OUTPUT_DIR / f"dashboard_{name}.png"
        window.grab().save(str(out_path))
        print(f"saved {out_path}")
    qt_app.quit()


def _this_weeks_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    args = parser.parse_args()

    db_path = Path(tempfile.gettempdir()) / "attune_marketing_demo.db"
    if db_path.exists():
        db_path.unlink()

    settings = Settings(database_url=f"sqlite+aiosqlite:///{db_path}", api_port=DEMO_PORT)
    container = bootstrap(settings)

    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(build_stylesheet())

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    window: MainWindow | None = None

    async def _startup() -> None:
        nonlocal window
        from sqlalchemy.ext.asyncio import AsyncEngine

        engine = container.resolve(AsyncEngine)
        await init_models(engine)

        session_repository = container.resolve(ISessionRepository)
        event_repository = container.resolve(IEventRepository)
        result = await seed_demo_data(
            session_repository, event_repository, _this_weeks_monday(), seed=args.seed
        )
        print(f"seeded {result.session_count} sessions / {result.event_count} events")

        ready = asyncio.Event()
        loop.create_task(_serve_api(container, settings.api_host, settings.api_port, ready))
        await ready.wait()

        api_client = ApiClient(f"http://{settings.api_host}:{settings.api_port}")
        window = MainWindow(api_client)
        window.show()

        loop.create_task(_tour(window, qt_app))

    with loop:
        loop.create_task(_startup())
        loop.run_forever()


if __name__ == "__main__":
    main()
