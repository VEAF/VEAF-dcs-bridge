"""FastAPI application factory for dcs-serve."""

from __future__ import annotations

import json
import uuid
from importlib.metadata import version
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dcs_bridge.common.models import Command, CommandAction
from dcs_bridge.serve.config import ServeConfig
from dcs_bridge.serve.core import CommandBus, DcsConnection, EventBroadcaster, Snapshot

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ExecRequest(BaseModel):
    """Body for POST /api/exec."""

    code: str
    timeout: float | None = None


class SpawnRequest(BaseModel):
    """Body for POST /api/spawn."""

    group_def: dict[str, Any]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    *,
    snapshot: Snapshot,
    bus: CommandBus,
    conn: DcsConnection,
    broadcaster: EventBroadcaster,
    config: ServeConfig,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        snapshot: Shared in-memory unit snapshot.
        bus: Shared command/response correlator.
        conn: Shared DCS TCP connection wrapper.
        broadcaster: WebSocket event broadcaster.
        config: Runtime configuration.

    Returns:
        Configured FastAPI application with all routes registered.
    """
    _version = version("dcs-bridge")
    app = FastAPI(title="dcs-serve", version=_version)
    app.state.snapshot = snapshot
    app.state.bus = bus
    app.state.conn = conn
    app.state.broadcaster = broadcaster
    app.state.config = config

    # ------------------------------------------------------------------
    # Auth dependency
    # ------------------------------------------------------------------

    def _require_api_key(request: Request) -> None:
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != request.app.state.config.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    auth = Depends(_require_api_key)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    async def _exec_command(
        request: Request,
        action: CommandAction,
        payload: dict[str, Any],
        timeout_override: float | None,
    ) -> JSONResponse:
        s_conn: DcsConnection = request.app.state.conn
        s_bus: CommandBus = request.app.state.bus
        s_cfg: ServeConfig = request.app.state.config

        if not s_conn.connected:
            return JSONResponse(status_code=503, content={"ready": False})

        effective_timeout = timeout_override if timeout_override is not None else s_cfg.default_timeout
        cmd_id = str(uuid.uuid4())
        cmd = Command(id=cmd_id, action=action, payload=payload)
        s_bus.register(cmd_id)
        try:
            await s_conn.send(cmd.model_dump_json())
        except RuntimeError:
            s_bus.unregister(cmd_id)
            return JSONResponse(status_code=503, content={"ready": False})

        try:
            resp = await s_bus.wait(cmd_id, timeout=effective_timeout)
        except TimeoutError:
            return JSONResponse(status_code=504, content={"error": "timeout"})

        if resp.error:
            return JSONResponse(status_code=200, content={"error": resp.error})
        return JSONResponse(status_code=200, content={"result": resp.result})

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/api/units", dependencies=[auth])
    async def get_units(request: Request) -> JSONResponse:
        """Return the current unit snapshot.

        Returns:
            200: List of units.
            503: DCS not ready or snapshot stale.
        """
        s: Snapshot = request.app.state.snapshot
        cfg: ServeConfig = request.app.state.config
        if not s.ready:
            return JSONResponse(status_code=503, content={"ready": False})
        if s.stale(cfg.stale_threshold):
            return JSONResponse(status_code=503, content={"ready": False, "stale": True})
        return JSONResponse(content=[u.model_dump() for u in s.units])

    @app.get("/api/mission", dependencies=[auth])
    async def get_mission(request: Request) -> JSONResponse:
        """Return basic mission information by querying DCS via Lua exec.

        Returns:
            200: JSON object with mission data.
            503: DCS not connected.
            504: Command timeout.
        """
        lua = "local ok, t = pcall(function() return env.mission.theatre end); return ok and t or 'unknown'"
        return await _exec_command(request, CommandAction.EXEC, {"code": lua}, None)

    @app.post("/api/exec", dependencies=[auth])
    async def exec_lua(request: Request, body: ExecRequest) -> JSONResponse:
        """Execute arbitrary Lua code in DCS and return the result.

        Args:
            body: ExecRequest with code and optional per-request timeout.

        Returns:
            200: Execution result or error from DCS.
            503: DCS not connected.
            504: Command timeout.
        """
        return await _exec_command(request, CommandAction.EXEC, {"code": body.code}, body.timeout)

    @app.post("/api/spawn", dependencies=[auth])
    async def spawn_unit(request: Request, body: SpawnRequest) -> JSONResponse:
        """Spawn a unit group in DCS.

        Args:
            body: SpawnRequest with group_def dict.

        Returns:
            200: Spawn result or error from DCS.
            503: DCS not connected.
            504: Command timeout.
        """
        return await _exec_command(request, CommandAction.SPAWN, {"group": body.group_def}, None)

    @app.websocket("/ws/stream")
    async def ws_stream(websocket: WebSocket) -> None:
        """Stream DCS events and full refreshes to the client.

        Authentication via X-API-Key header or api_key query parameter.
        On connect, sends the current snapshot if ready.
        Then forwards all events/refreshes from the broadcaster.
        """
        cfg: ServeConfig = websocket.app.state.config
        key = websocket.headers.get("X-API-Key") or websocket.query_params.get("api_key")
        if key != cfg.api_key:
            await websocket.close(code=4001)
            return

        await websocket.accept()
        s: Snapshot = websocket.app.state.snapshot
        bcast: EventBroadcaster = websocket.app.state.broadcaster

        if s.ready:
            await websocket.send_text(json.dumps({"type": "full_refresh", "units": [u.model_dump() for u in s.units]}))

        queue = bcast.subscribe()
        try:
            while True:
                msg = await queue.get()
                await websocket.send_text(json.dumps(msg))
        except WebSocketDisconnect:
            pass
        finally:
            bcast.unsubscribe(queue)

    return app
