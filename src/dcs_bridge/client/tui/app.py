"""Textual TUI for dcs-client."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import websockets
import websockets.exceptions
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Input, Label, RichLog

from dcs_bridge.client.config import ClientConfig
from dcs_bridge.common.models import Coalition

logger = logging.getLogger(__name__)

_COALITION_LABEL: dict[int, str] = {
    Coalition.NEUTRAL: "Neutral",
    Coalition.RED: "Red",
    Coalition.BLUE: "Blue",
}

_RECONNECT_DELAY = 5.0


class DcsBridgeApp(App[None]):
    """Textual TUI for monitoring and controlling a DCS mission via dcs-serve."""

    TITLE = "dcs-bridge TUI"
    CSS = """
    #units { height: 1fr; }
    #lua-log { height: 8; border: solid $success; }
    #status { height: 1; dock: bottom; }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, config: ClientConfig) -> None:
        """Initialise with runtime config.

        Args:
            config: ClientConfig with host, port and api_key.
        """
        super().__init__()
        self._config = config
        self._base_url = f"http://{config.host}:{config.port}"
        self._ws_base = f"ws://{config.host}:{config.port}/ws/stream"  # nosemgrep: detect-insecure-websocket
        self._headers = {"Authorization": f"Bearer {config.api_key}"}

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header()
        with Vertical():
            yield DataTable(id="units")
            yield Input(placeholder="Enter Lua code and press Enter…", id="lua-input")
            yield RichLog(id="lua-log", highlight=True, markup=True)
        yield Label("Connecting…", id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Set up unit table columns and start the WebSocket + catalogue workers."""
        table = self.query_one("#units", DataTable)
        table.add_columns("Name", "Type", "Coalition", "Lat", "Lon", "Alt (m)")
        self.run_worker(self._ws_worker(), exclusive=True, name="ws-stream")
        self.run_worker(self._load_catalog(), name="catalog")

    async def _load_catalog(self) -> None:
        """Fetch and display the capability-filtered action catalogue.

        Shows only the actions available for the running mission (ADR-0005).
        """
        log = self.query_one("#lua-log", RichLog)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/api/catalog", headers=self._headers, timeout=10.0)
        except httpx.HTTPError as exc:
            logger.debug("catalog fetch failed: %s", exc)
            return
        if resp.status_code != 200:
            return
        actions = resp.json().get("actions", [])
        if not actions:
            log.write("[dim]No actions available (waiting for mission capabilities)…[/dim]")
            return
        log.write("[bold]Available actions:[/bold]")
        for action in actions:
            backends = ", ".join(action.get("available_backends", []))
            log.write(f"  [cyan]{action['name']}[/cyan] ({backends}) — {action.get('summary', '')}")

    # ------------------------------------------------------------------
    # Unit table helpers
    # ------------------------------------------------------------------

    def _update_units(self, units: list[dict[str, Any]]) -> None:
        """Replace the units table content with the given unit list.

        Args:
            units: Raw unit dicts as received from the WebSocket.
        """
        table = self.query_one("#units", DataTable)
        table.clear()
        for u in units:
            coalition_id = int(u.get("coalition", 0))
            table.add_row(
                u.get("name", ""),
                u.get("type", ""),
                _COALITION_LABEL.get(coalition_id, str(coalition_id)),
                f"{u.get('position_geo', {}).get('lat', 0.0):.4f}",
                f"{u.get('position_geo', {}).get('lon', 0.0):.4f}",
                f"{u.get('altitude_agl', 0.0):.0f}",
            )

    # ------------------------------------------------------------------
    # WebSocket worker
    # ------------------------------------------------------------------

    async def _fetch_ws_ticket(self) -> str:
        """Obtain a single-use WebSocket ticket from dcs-serve over REST.

        Returns:
            The ticket string.

        Raises:
            httpx.HTTPError: On a transport error.
            ValueError: If the response has no usable ticket.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self._base_url}/api/ws-ticket", headers=self._headers, timeout=10.0)
        if resp.status_code != 200:
            raise ValueError(f"ws-ticket request failed: {resp.status_code}")
        ticket = resp.json().get("ticket")
        if not ticket:
            raise ValueError("ws-ticket response missing 'ticket'")
        return str(ticket)

    async def _ws_worker(self) -> None:
        """Connect to the dcs-serve WebSocket and process incoming messages.

        A fresh single-use ticket is fetched over REST before each connection
        (browsers/clients cannot send custom WS headers). Reconnects automatically
        after _RECONNECT_DELAY seconds on failure.
        """
        status = self.query_one("#status", Label)
        while True:
            try:
                ticket = await self._fetch_ws_ticket()
                async with websockets.connect(f"{self._ws_base}?ticket={ticket}") as ws:
                    status.update("● Connected")
                    async for raw in ws:
                        msg: dict[str, Any] = json.loads(raw)
                        msg_type = msg.get("type")
                        if msg_type == "full_refresh":
                            self._update_units(msg.get("units", []))
            except websockets.exceptions.WebSocketException as exc:
                logger.debug("WebSocket error: %s", exc)
                status.update(f"✕ Disconnected — retrying in {_RECONNECT_DELAY:.0f}s…")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unexpected WS error: %s", exc)
                status.update(f"✕ Error: {exc}")

            await asyncio.sleep(_RECONNECT_DELAY)

    # ------------------------------------------------------------------
    # Lua input handler
    # ------------------------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Execute submitted Lua code via the dcs-serve REST API.

        Args:
            event: Input.Submitted event carrying the entered code.
        """
        code = event.value.strip()
        if not code:
            return
        event.input.clear()

        log = self.query_one("#lua-log", RichLog)
        log.write(f"[bold cyan]> {code}[/bold cyan]")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/api/exec",
                    json={"code": code},
                    headers=self._headers,
                    timeout=15.0,
                )
            data: dict[str, Any] = resp.json()
            if "result" in data:
                log.write(f"[green]{data['result']}[/green]")
            else:
                log.write(f"[red]Error: {data.get('error', 'unknown')}[/red]")
        except httpx.HTTPError as exc:
            log.write(f"[red]HTTP error: {exc}[/red]")
