"""dcs-serve core: TCP handler, in-memory snapshot, command/response correlation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from dcs_bridge.common.models import Coalition, FullRefresh, Response, Unit, UnitPositionDcs, UnitPositionGeo
from dcs_bridge.serve.capabilities import CapabilityState

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
        """Current unit list (shallow copy — callers must not mutate)."""
        return list(self._units)

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

    def backdate_for_test(self, seconds: float) -> None:
        """Shift last_updated into the past by seconds. For use in tests only."""
        if self._last_updated is not None:
            self._last_updated -= seconds


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

    def unregister(self, cmd_id: str) -> None:
        """Remove a pending command id without resolving it (e.g. on send failure).

        Args:
            cmd_id: The command id to remove.
        """
        self._pending.pop(cmd_id, None)

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
            asyncio.TimeoutError: If no response arrives within timeout seconds.
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


class EventBroadcaster:
    """Broadcasts JSON-serialisable dicts to all active WebSocket subscribers."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Create and register a new subscriber queue.

        Returns:
            A new asyncio.Queue that will receive broadcast messages.
        """
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue.

        Args:
            q: The queue returned by subscribe().
        """
        self._queues.discard(q)

    def broadcast(self, msg: dict[str, Any]) -> None:
        """Push msg to every subscriber queue (non-blocking).

        Args:
            msg: JSON-serialisable dict to broadcast.
        """
        for q in list(self._queues):
            q.put_nowait(msg)


class DcsConnection:
    """Holds the active TCP StreamWriter to the Lua bridge.

    Shared between the TCP server and the HTTP/WS API layer. The writer is
    set to None when DCS disconnects and restored when it reconnects.
    """

    def __init__(self) -> None:
        self._writer: asyncio.StreamWriter | None = None

    @property
    def connected(self) -> bool:
        """True when a Lua bridge is connected."""
        return self._writer is not None

    def set_writer(self, writer: asyncio.StreamWriter | None) -> None:
        """Update the active writer (called by the TCP server on connect/disconnect).

        Args:
            writer: New StreamWriter, or None on disconnect.
        """
        self._writer = writer

    async def send(self, data: str) -> None:
        """Write a newline-terminated string to the TCP connection.

        Args:
            data: UTF-8 string to send (newline appended automatically).

        Raises:
            RuntimeError: If DCS is not connected.
        """
        if self._writer is None:
            raise RuntimeError("DCS not connected")
        self._writer.write((data + "\n").encode())
        await self._writer.drain()


class TcpHandler:
    """Processes newline-delimited JSON messages received from the Lua bridge.

    Delegates full_refresh messages to the Snapshot and response messages
    to the CommandBus. Designed to be called synchronously from an asyncio
    StreamReader loop.
    """

    def __init__(
        self,
        *,
        snapshot: Snapshot,
        bus: CommandBus,
        broadcaster: EventBroadcaster | None = None,
        capabilities: CapabilityState | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._bus = bus
        self._broadcaster = broadcaster or EventBroadcaster()
        self._capabilities = capabilities
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
        elif msg_type == "handshake":
            self._handle_handshake(msg)
        elif msg_type == "event":
            self._handle_event(msg)
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
        self._broadcaster.broadcast({"type": "full_refresh", "units": [u.model_dump() for u in units]})

    def _handle_handshake(self, msg: dict[str, Any]) -> None:
        if self._capabilities is None:
            return
        raw = msg.get("frameworks")
        if raw is not None and not isinstance(raw, dict):
            logger.warning("malformed handshake: 'frameworks' is %s, not an object", type(raw).__name__)
        frameworks = raw if isinstance(raw, dict) else {}
        # Coerce announced versions to str | None; drop non-scalar values.
        announced: dict[str, str | None] = {}
        for key, value in frameworks.items():
            if value is None or isinstance(value, str):
                announced[str(key)] = value
            elif isinstance(value, (int, float, bool)):
                announced[str(key)] = str(value)
        self._capabilities.update(announced)

    def _handle_event(self, msg: dict[str, Any]) -> None:
        self._broadcaster.broadcast(msg)

    def _handle_response(self, msg: dict[str, Any]) -> None:
        cmd_id = msg.get("id")
        if not isinstance(cmd_id, str):
            logger.warning("response missing string id: %r", msg)
            return
        self._bus.resolve(cmd_id, result=msg.get("result"), error=msg.get("error"))


async def run_tcp_server(
    host: str,
    port: int,
    *,
    snapshot: Snapshot,
    bus: CommandBus,
    conn: DcsConnection,
    broadcaster: EventBroadcaster,
    capabilities: CapabilityState | None = None,
    on_connect: Callable[[], None] | None = None,
    on_disconnect: Callable[[], None] | None = None,
) -> None:
    """Listen for the Lua bridge TCP connection and process messages.

    Accepts one connection at a time. When the Lua bridge disconnects the
    server waits for a new connection. The DcsConnection writer is updated
    on each connect/disconnect so the HTTP layer always has the current writer.

    Args:
        host: TCP bind address.
        port: TCP bind port.
        snapshot: Shared snapshot to update on full refreshes.
        bus: Shared command bus to resolve responses.
        conn: Shared connection object to update with the active writer.
        broadcaster: Event broadcaster for WebSocket clients.
        capabilities: Optional capability cache, updated on handshake and cleared
            on disconnect.
        on_connect: Optional callback invoked when DCS connects.
        on_disconnect: Optional callback invoked when DCS disconnects.
    """

    async def _client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        logger.info("DCS connected from %s", peer)
        conn.set_writer(writer)
        if on_connect:
            on_connect()
        handler = TcpHandler(snapshot=snapshot, bus=bus, broadcaster=broadcaster, capabilities=capabilities)
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                handler.feed(data.decode(errors="replace"))
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            conn.set_writer(None)
            if capabilities is not None:
                capabilities.clear()
            if on_disconnect:
                on_disconnect()
            logger.info("DCS disconnected from %s", peer)

    server = await asyncio.start_server(_client_connected, host, port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    logger.info("TCP server listening on %s", addrs)
    async with server:
        await server.serve_forever()
