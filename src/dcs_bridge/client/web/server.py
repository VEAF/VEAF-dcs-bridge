"""Web client server — serves the static Leaflet map and opens the browser."""

from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


def run_web(host: str, port: int) -> None:
    """Start the static HTTP server and open the browser.

    The browser is opened 500 ms after the server signals readiness so the
    tab does not open before the server accepts connections.

    Args:
        host: Bind address for the HTTP server.
        port: TCP port for the HTTP server.
    """
    ready_event = threading.Event()

    web_app = FastAPI()
    web_app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

    config = uvicorn.Config(web_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    original_startup = server.startup

    async def _startup_with_signal(sockets: list | None = None) -> None:
        await original_startup(sockets)
        ready_event.set()

    server.startup = _startup_with_signal  # type: ignore[method-assign]

    def _open_browser() -> None:
        if ready_event.wait(timeout=10.0):
            threading.Timer(0.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
        else:
            logger.warning("Web server did not become ready in time; skipping browser open.")

    threading.Thread(target=_open_browser, daemon=True).start()

    logger.info("Starting web client on http://%s:%d", host, port)
    server.run()
