"""dcs-serve core: TCP handler, in-memory snapshot, command/response correlation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from dcs_bridge.common.models import Coalition, FullRefresh, Response, Unit, UnitPositionDcs, UnitPositionGeo

logger = logging.getLogger(__name__)


class Snapshot:
    """In-memory cache of the current DCS mission unit state.

    Updated by full refreshes pushed by the Lua bridge every N seconds.
    See ADR-0002.
    """

    def __init__(self) -> None:
        self._units: list[Unit] = []
        self._last_updated: float | None = None

    @property
    def ready(self) -> bool:
        """True once the first full refresh has been received."""
        return self._last_updated is not None

    @property
    def units(self) -> list[Unit]:
        """Current unit list."""
        return self._units

    @property
    def last_updated(self) -> float | None:
        """Monotonic timestamp of the last full refresh, or None if not yet received."""
        return self._last_updated

    def stale(self, threshold: float) -> bool:
        """Return True if the snapshot has not been updated within threshold seconds."""
        if self._last_updated is None:
            return False
        return (time.monotonic() - self._last_updated) > threshold

    def apply_full_refresh(self, refresh: FullRefresh) -> None:
        """Replace the current unit list with the data from a full refresh."""
        self._units = list(refresh.units)
        self._last_updated = time.monotonic()
        logger.debug("snapshot updated: %d units", len(self._units))


class CommandBus:
    """Correlates outgoing Commands with incoming Responses by id.

    dcs-serve pushes a command over TCP and suspends the HTTP handler coroutine
    until the Lua bridge sends back a response with the matching id.
    """

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Event] = {}
        self._responses: dict[str, Response] = {}

    def register(self, cmd_id: str) -> None:
        """Register a pending command id before sending it over TCP."""
        self._pending[cmd_id] = asyncio.Event()

    def resolve(self, cmd_id: str, *, result: str | None, error: str | None) -> None:
        """Called by the TCP handler when a response arrives from DCS."""
        event = self._pending.get(cmd_id)
        if event is None:
            logger.debug("resolve: unknown id %s (ignored)", cmd_id)
            return
        self._responses[cmd_id] = Response(id=cmd_id, result=result, error=error)
        event.set()

    async def wait(self, cmd_id: str, *, timeout: float) -> Response:
        """Wait for the response to cmd_id.

        Args:
            cmd_id: The command id to wait for.
            timeout: Maximum seconds to wait.

        Returns:
            The Response from the Lua bridge.

        Raises:
            TimeoutError: If no response arrives within timeout seconds.
        """
        event = self._pending.get(cmd_id)
        if event is None:
            raise KeyError(f"cmd_id {cmd_id!r} was not registered")
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"no response for command {cmd_id!r} within {timeout}s")
        finally:
            self._pending.pop(cmd_id, None)
        return self._responses.pop(cmd_id)


class TcpHandler:
    """Processes newline-delimited JSON messages received from the Lua bridge.

    Delegates full_refresh messages to the Snapshot and response messages
    to the CommandBus. Designed to be called synchronously from an asyncio
    StreamReader loop.
    """

    def __init__(self, *, snapshot: Snapshot, bus: CommandBus) -> None:
        self._snapshot = snapshot
        self._bus = bus
        self._buf = ""

    def feed(self, data: str) -> None:
        """Feed raw data (may contain multiple newline-delimited messages)."""
        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if line:
                self._process_line(line)

    def _process_line(self, line: str) -> None:
        try:
            msg: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("malformed JSON from DCS: %r", line[:200])
            return

        msg_type = msg.get("type")

        if msg_type == "full_refresh":
            self._handle_full_refresh(msg)
        elif "id" in msg:
            self._handle_response(msg)
        else:
            logger.debug("unhandled message type: %r", msg_type)

    def _handle_full_refresh(self, msg: dict[str, Any]) -> None:
        try:
            units = [
                Unit(
                    name=u["name"],
                    position_dcs=UnitPositionDcs(**u["position_dcs"]),
                    position_geo=UnitPositionGeo(**u["position_geo"]),
                    altitude_agl=float(u["altitude_agl"]),
                    category=str(u["category"]),
                    type=str(u["type"]),
                    coalition=Coalition(int(u["coalition"])),
                )
                for u in msg.get("units", [])
            ]
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("invalid full_refresh payload: %s", exc)
            return
        self._snapshot.apply_full_refresh(FullRefresh(units=units))

    def _handle_response(self, msg: dict[str, Any]) -> None:
        cmd_id = msg.get("id")
        if not isinstance(cmd_id, str):
            logger.warning("response missing string id: %r", msg)
            return
        self._bus.resolve(cmd_id, result=msg.get("result"), error=msg.get("error"))
