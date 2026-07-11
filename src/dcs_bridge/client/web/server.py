"""Web client server — serves the static Leaflet map and opens the browser."""

from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


def create_web_app(serve_host: str, serve_port: int, api_key: str) -> FastAPI:
    """Build the web-client FastAPI app.

    The WEB server holds the durable dcs-serve token and never exposes it to the
    browser (ADR-0005 *Transport*). ``GET /config.json`` serves only the
    connection host/port; ``POST /ws-ticket`` proxies an authenticated request to
    dcs-serve and returns a fresh single-use WebSocket ticket, so no credential
    ever appears in the page, a URL, or ``/config.json``.

    Args:
        serve_host: Host of the dcs-serve HTTP/WebSocket endpoint.
        serve_port: Port of the dcs-serve HTTP/WebSocket endpoint.
        api_key: The durable dcs-serve token, held server-side only.

    Returns:
        The configured FastAPI application.
    """
    web_app = FastAPI()
    serve_base = f"http://{serve_host}:{serve_port}"
    headers = {"Authorization": f"Bearer {api_key}"}

    @web_app.get("/config.json")
    def config() -> dict[str, object]:
        """Return the dcs-serve connection host/port (no credential)."""
        return {"host": serve_host, "port": serve_port}

    @web_app.post("/ws-ticket")
    async def ws_ticket() -> JSONResponse:
        """Proxy an ephemeral WebSocket ticket from dcs-serve for the browser."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{serve_base}/api/ws-ticket", headers=headers, timeout=10.0)
        except httpx.HTTPError as exc:
            logger.warning("ws-ticket proxy failed: %s", exc)
            return JSONResponse(status_code=502, content={"error": "dcs-serve unreachable"})
        if resp.status_code != 200:
            return JSONResponse(status_code=resp.status_code, content={"error": "ticket request rejected"})
        return JSONResponse(content=resp.json())

    @web_app.get("/catalog")
    async def catalog() -> JSONResponse:
        """Proxy the capability-filtered action catalogue for the browser panel."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{serve_base}/api/catalog", headers=headers, timeout=10.0)
        except httpx.HTTPError as exc:
            logger.warning("catalog proxy failed: %s", exc)
            return JSONResponse(status_code=502, content={"error": "dcs-serve unreachable"})
        if resp.status_code != 200:
            return JSONResponse(status_code=resp.status_code, content={"error": "catalog request rejected"})
        return JSONResponse(content=resp.json())

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
