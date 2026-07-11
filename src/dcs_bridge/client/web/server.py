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


def create_web_app(serve_host: str, serve_port: int, api_key: str) -> FastAPI:
    """Build the web-client FastAPI app.

    Exposes ``GET /config.json`` with the dcs-serve connection parameters so the
    Leaflet page can open its WebSocket without a hand-crafted URL hash, then
    mounts the static assets at ``/``. The route is registered before the static
    mount so ``/`` does not shadow it.

    Args:
        serve_host: Host of the dcs-serve HTTP/WebSocket endpoint.
        serve_port: Port of the dcs-serve HTTP/WebSocket endpoint.
        api_key: API key expected by dcs-serve (``/ws/stream``).

    Returns:
        The configured FastAPI application.
    """
    web_app = FastAPI()

    @web_app.get("/config.json")
    def config() -> dict[str, object]:
        """Return the dcs-serve connection parameters consumed by the browser."""
        return {"host": serve_host, "port": serve_port, "api_key": api_key}

    web_app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return web_app


def run_web(web_host: str, web_port: int, serve_host: str, serve_port: int, api_key: str) -> None:
    """Start the static HTTP server and open the browser.

    The browser is opened 500 ms after the server signals readiness so the
    tab does not open before the server accepts connections.

    Args:
        web_host: Bind address for the local HTTP server.
        web_port: TCP port for the local HTTP server.
        serve_host: Host of the dcs-serve endpoint, served via ``/config.json``.
        serve_port: Port of the dcs-serve endpoint, served via ``/config.json``.
        api_key: API key for dcs-serve, served via ``/config.json``.
    """
    ready_event = threading.Event()

    web_app = create_web_app(serve_host, serve_port, api_key)

    config = uvicorn.Config(web_app, host=web_host, port=web_port, log_level="warning")
    server = uvicorn.Server(config)

    original_startup = server.startup

    async def _startup_with_signal(sockets: list | None = None) -> None:
        await original_startup(sockets)
        ready_event.set()

    server.startup = _startup_with_signal  # type: ignore[method-assign]

    def _open_browser() -> None:
        if ready_event.wait(timeout=10.0):
            threading.Timer(0.5, lambda: webbrowser.open(f"http://{web_host}:{web_port}")).start()
        else:
            logger.warning("Web server did not become ready in time; skipping browser open.")

    threading.Thread(target=_open_browser, daemon=True).start()

    logger.info("Starting web client on http://%s:%d", web_host, web_port)
    server.run()
