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
from dcs_bridge.serve.actions import ActionError, build_action_lua
from dcs_bridge.serve.capabilities import CapabilityState
from dcs_bridge.serve.catalog import build_catalog, describe, search_catalog
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


class ActionRequest(BaseModel):
    """Body for POST /api/action."""

    name: str
    args: dict[str, Any] = {}
    backend: str | None = None


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
    capabilities: CapabilityState | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        snapshot: Shared in-memory unit snapshot.
        bus: Shared command/response correlator.
        conn: Shared DCS TCP connection wrapper.
        broadcaster: WebSocket event broadcaster.
        config: Runtime configuration.
        capabilities: Shared capability cache (created empty if not supplied).

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
    app.state.capabilities = capabilities if capabilities is not None else CapabilityState()

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

    @app.get("/api/capabilities", dependencies=[auth])
    async def get_capabilities(request: Request) -> JSONResponse:
        """Return the frameworks detected in the running mission (ADR-0005).

        The set is announced by the Lua bridge at the handshake, matched against
        the versions this build targets (lockstep), cached, and cleared on
        disconnect. A framework present but at the wrong version is reported
        ``present: false`` with a ``reason``.

        Returns:
            200: ``{connected, frameworks: {name: {present, version, targeted, reason}}}``.
        """
        state: CapabilityState = request.app.state.capabilities
        s_conn: DcsConnection = request.app.state.conn
        return JSONResponse(
            content={
                "connected": s_conn.connected,
                "frameworks": {name: status.model_dump() for name, status in state.frameworks.items()},
            }
        )

    @app.get("/api/catalog", dependencies=[auth])
    async def get_catalog(request: Request) -> JSONResponse:
        """Return the action catalogue filtered by detected capabilities (ADR-0005).

        The catalogue is the union of every verb at least one present backend can
        perform. It is empty until the first handshake.

        Returns:
            200: ``{actions: [{name, summary, scope, min_role, backends,
            available_backends, params}]}``.
        """
        caps: CapabilityState = request.app.state.capabilities
        return JSONResponse(content={"actions": [info.model_dump() for info in build_catalog(caps)]})

    @app.get("/api/catalog/search", dependencies=[auth])
    async def catalog_search(request: Request, q: str = "") -> JSONResponse:
        """Search the catalogue and the long-tail values for a query string.

        Args:
            q: Case-insensitive substring (empty matches nothing).

        Returns:
            200: ``{actions: [...], values: [{catalog, value, label}]}``.
        """
        caps = request.app.state.capabilities
        return JSONResponse(content=search_catalog(q, caps).model_dump())

    @app.get("/api/catalog/{name}", dependencies=[auth])
    async def catalog_describe(request: Request, name: str) -> JSONResponse:
        """Describe one action, resolving its long-tail parameter values.

        Args:
            name: The action name.

        Returns:
            200: ``{action: {...}, values: {param: [{value, label, tags}]}}``.
            404: Unknown action.
        """
        caps = request.app.state.capabilities
        result = describe(name, caps)
        if result is None:
            return JSONResponse(status_code=404, content={"error": f"unknown action: {name}"})
        return JSONResponse(content=result)

    @app.post("/api/action", dependencies=[auth])
    async def run_action(request: Request, body: ActionRequest) -> JSONResponse:
        """Perform a high-level semantic action, routed to a backend adapter.

        The action is resolved in the registry, a backend is selected (or forced
        via ``backend``), the adapter builds a Lua snippet, and it is executed in
        DCS through the existing exec channel (ADR-0005).

        Args:
            body: ActionRequest with the verb name, args and optional forced backend.

        Returns:
            200: Action result or error from DCS.
            400: Invalid action arguments or unavailable backend.
            404: Unknown action name.
            503: DCS not connected.
            504: Command timeout.
        """
        try:
            lua = build_action_lua(body.name, body.args, backend=body.backend)
        except KeyError:
            return JSONResponse(status_code=404, content={"error": f"unknown action: {body.name}"})
        except ActionError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return await _exec_command(request, CommandAction.EXEC, {"code": lua}, None)

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
