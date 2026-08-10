from __future__ import annotations

import asyncio
import sys

import qasync
import uvicorn
from PySide6.QtWidgets import QApplication

from attune.api.main import create_app as create_api_app
from attune.bootstrap import bootstrap
from attune.config.settings import get_settings
from attune.container import Container
from attune.dashboard.api_client import ApiClient
from attune.dashboard.main_window import MainWindow
from attune.dashboard.theme import build_stylesheet

# Composition root for the desktop app, kept out of attune.dashboard so that
# package stays a pure HTTP client of the backend (see api_client.py) per
# docs/architecture/03-module-dependencies.md — only this launcher is allowed
# to know about bootstrap()/the FastAPI app/the database+llm layers it pulls in.


async def _serve_api(container: Container, host: str, port: int, ready: asyncio.Event) -> None:
    """Runs the FastAPI backend in-process, on the same qasync loop the UI
    uses. This just avoids requiring a separately-started server process for
    a single-user local desktop app.
    """
    api_app = create_api_app(container=container)
    config = uvicorn.Config(api_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    serve_task = asyncio.ensure_future(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    ready.set()
    await serve_task


def run() -> None:
    settings = get_settings()
    container = bootstrap(settings)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(settings.app_name)
    qt_app.setStyleSheet(build_stylesheet())

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    window: MainWindow | None = None

    async def _startup() -> None:
        nonlocal window
        ready = asyncio.Event()
        loop.create_task(_serve_api(container, settings.api_host, settings.api_port, ready))
        await ready.wait()

        api_client = ApiClient(f"http://{settings.api_host}:{settings.api_port}")
        window = MainWindow(api_client)
        window.show()

    with loop:
        loop.create_task(_startup())
        loop.run_forever()


if __name__ == "__main__":
    run()
