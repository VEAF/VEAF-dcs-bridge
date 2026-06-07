"""dcs-serve FastAPI application: REST endpoints, WebSocket stream, API key auth."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from dcs_bridge.serve.core import CommandBus, Snapshot

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

DEFAULT_EXEC_TIMEOUT = 30.0
DEFAULT_STALE_THRESHOLD = 10.0


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ExecRequest(BaseModel):
    """Body for POST /api/exec."""

    code: str
    timeout: float | None = None


class ExecResponse(BaseModel):
    """Response for POST /api/exec."""

    success: bool
    result: str | None
    error: str | None


class UnitsResponse(BaseModel):
    """Response for GET /api/units."""

    units: list[dict[str, Any]]
    stale: bool
    last_updated: float | None


class SpawnRequest(BaseModel):
    """Body for POST /api/spawn."""

    group: dict[str, Any]
    timeout: float | None = None


# ---------------------------------------------------------------------------
# Command sender (injectable for testing)
# ---------------------------------------------------------------------------


async def send_command(cmd_id: str, payload: dict[str, Any], timeout: float) -> None:
    """Placeholder — replaced by the real TCP sender at runtime.

    The cmd_id is registered on the CommandBus by _dispatch before this is called.

    Args:
        cmd_id: Unique command id, already registered on the CommandBus.
        payload: Command payload dict (action-specific).
        timeout: Seconds before the caller raises TimeoutError.
    """
    raise NotImplementedError("send_command must be bound at app startup")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    *,
    snapshot: Snapshot,
    bus: CommandBus,
    api_key: str,
    exec_timeout_default: float = DEFAULT_EXEC_TIMEOUT,
    exec_timeout_max: float = 300.0,
    stale_threshold: float = DEFAULT_STALE_THRESHOLD,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        snapshot: Shared in-memory unit snapshot.
        bus: Shared command/response correlation bus.
        api_key: Required API key for all endpoints.
        exec_timeout_default: Default timeout for exec commands (seconds).
        exec_timeout_max: Maximum allowed timeout per request.
        stale_threshold: Seconds after which the snapshot is considered stale.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(title="dcs-serve", version="0.1.0")

    # ------------------------------------------------------------------
    # Auth dependency
    # ------------------------------------------------------------------

    async def require_api_key(key: str | None = Depends(_api_key_header)) -> str:
        if key != api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return key

    # ------------------------------------------------------------------
    # DCS availability dependency
    # ------------------------------------------------------------------

    async def require_dcs() -> None:
        if not snapshot.ready:
            raise HTTPException(
                status_code=503,
                detail={"ready": False, "reason": "waiting_for_first_snapshot"},
            )

    # ------------------------------------------------------------------
    # Helper: send a command to DCS and wait for the response
    # ------------------------------------------------------------------

    async def _dispatch(action: str, payload: dict[str, Any], timeout: float) -> Any:
        cmd_id = str(uuid.uuid4())
        bus.register(cmd_id)
        try:
            await send_command(cmd_id, {"action": action, **payload}, timeout)
            return await bus.wait(cmd_id, timeout=timeout)
        except TimeoutError:
            raise HTTPException(status_code=504, detail="DCS did not respond in time")

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    @app.get("/api/units", dependencies=[Depends(require_api_key), Depends(require_dcs)])
    async def get_units() -> UnitsResponse:
        """Return the current unit snapshot."""
        return UnitsResponse(
            units=[u.model_dump() for u in snapshot.units],
            stale=snapshot.stale(stale_threshold),
            last_updated=snapshot.last_updated,
        )

    exec_timeout_min = 0.1

    def _clamp_timeout(request_timeout: float | None) -> float:
        effective = request_timeout if request_timeout is not None else exec_timeout_default
        return max(exec_timeout_min, min(effective, exec_timeout_max))

    @app.post("/api/exec", dependencies=[Depends(require_api_key), Depends(require_dcs)])
    async def post_exec(body: ExecRequest) -> ExecResponse:
        """Execute arbitrary Lua code in DCS and return the result."""
        response = await _dispatch("exec", {"payload": {"code": body.code}}, _clamp_timeout(body.timeout))
        return ExecResponse(
            success=response.error is None,
            result=response.result,
            error=response.error,
        )

    @app.post("/api/spawn", dependencies=[Depends(require_api_key), Depends(require_dcs)])
    async def post_spawn(body: SpawnRequest) -> ExecResponse:
        """Spawn a unit group in DCS."""
        response = await _dispatch("spawn", {"payload": {"group": body.group}}, _clamp_timeout(body.timeout))
        return ExecResponse(
            success=response.error is None,
            result=response.result,
            error=response.error,
        )

    @app.get("/api/mission", dependencies=[Depends(require_api_key), Depends(require_dcs)])
    async def get_mission() -> dict[str, Any]:
        """Return current mission info from DCS."""
        lua_code = (
            "local m = env.mission; "
            "return require('json'):encode({theatre=m.theatre, name=m.groundControl and m.groundControl.pilot or 'unknown'})"
        )
        response = await _dispatch("exec", {"payload": {"code": lua_code}}, exec_timeout_default)
        if response.error:
            raise HTTPException(status_code=502, detail=response.error)
        try:
            return json.loads(response.result or "{}")
        except json.JSONDecodeError:
            return {"raw": response.result}

    # ------------------------------------------------------------------
    # WebSocket stream
    # ------------------------------------------------------------------

    @app.websocket("/ws/stream")
    async def ws_stream(websocket: WebSocket) -> None:
        """Stream real-time unit updates to connected clients."""
        key = websocket.headers.get("X-API-Key") or websocket.query_params.get("api_key")
        if key != api_key:
            await websocket.close(code=4401)
            return

        await websocket.accept()
        logger.info("WebSocket client connected")
        try:
            while True:
                # Wait for client ping or disconnect
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")

    return app
