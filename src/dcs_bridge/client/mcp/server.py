"""MCP server for dcs-client."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from dcs_bridge.client.config import ClientConfig

logger = logging.getLogger(__name__)


class DcsMcpServer:
    """Wraps FastMCP and exposes dcs-serve as MCP tools.

    Each tool method delegates to the dcs-serve REST API via httpx.
    Return values are always strings (for exec/spawn/mission) or
    a list/dict (for get_units), so MCP clients receive JSON-serialisable data.

    Args:
        config: ClientConfig with host, port and api_key.
    """

    def __init__(self, config: ClientConfig) -> None:
        self._base_url = f"http://{config.host}:{config.port}"
        self._headers = {"Authorization": f"Bearer {config.api_key}"}
        self.mcp = FastMCP("dcs-bridge")
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def exec_lua(self, code: str, timeout: float | None = None) -> str:
        """Execute arbitrary Lua code in DCS.

        Args:
            code: Lua source code to execute inside the DCS scripting environment.
            timeout: Optional per-request timeout in seconds. Uses server default if None.

        Returns:
            The string result returned by the Lua snippet, or an error message.
        """
        body: dict[str, Any] = {"code": code}
        if timeout is not None:
            body["timeout"] = timeout

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/exec",
                json=body,
                headers=self._headers,
            )

        if resp.status_code != 200:
            return f"Error: dcs-serve returned {resp.status_code} — DCS not ready"

        data: dict[str, Any] = resp.json()
        if "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", ""))

    async def get_units(self) -> list[dict[str, Any]] | dict[str, str]:
        """Return the current unit snapshot from DCS.

        Returns:
            A list of unit dicts when DCS is ready, or a dict with an ``error`` key.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/units",
                headers=self._headers,
            )

        if resp.status_code != 200:
            return {"error": f"dcs-serve returned {resp.status_code} — DCS not ready"}

        return resp.json()  # type: ignore[no-any-return]

    async def spawn_unit(self, group_def: dict[str, Any]) -> str:
        """Spawn a unit group in DCS.

        Args:
            group_def: DCS group definition dict (matches the Lua coalition.addGroup structure).

        Returns:
            The string result from DCS, or an error message.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/spawn",
                json={"group_def": group_def},
                headers=self._headers,
            )

        if resp.status_code != 200:
            return f"Error: dcs-serve returned {resp.status_code} — DCS not ready"

        data: dict[str, Any] = resp.json()
        if "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", ""))

    async def spawn(
        self,
        type: str,
        position: dict[str, float],
        kind: str = "vehicle",
        coalition: str = "blue",
    ) -> str:
        """Spawn a unit via the capability-aware bridge (no MIST dependency).

        Args:
            type: DCS type name (e.g. ``"Hummer"``).
            position: Location as ``{"lat":.., "lon":..}`` or ``{"x":.., "z":..}``.
            kind: One of ``vehicle``/``ship``/``plane``/``helicopter``.
            coalition: ``"red"``, ``"blue"`` or ``"neutral"``.

        Returns:
            The spawned group name from DCS, or an error message.
        """
        args: dict[str, Any] = {"type": type, "position": position, "kind": kind, "coalition": coalition}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/action",
                json={"name": "spawn", "args": args},
                headers=self._headers,
            )

        if resp.status_code != 200:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            detail = data.get("error") or f"dcs-serve returned {resp.status_code}"
            return f"Error: {detail}"

        data = resp.json()
        if "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", ""))

    async def get_mission_info(self) -> str:
        """Return basic mission information (theatre name) from DCS.

        Returns:
            A string describing the current mission, or an error message.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/mission",
                headers=self._headers,
            )

        if resp.status_code != 200:
            return f"Error: dcs-serve returned {resp.status_code} — DCS not ready"

        data: dict[str, Any] = resp.json()
        if "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", ""))

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all tool methods with the FastMCP instance."""

        @self.mcp.tool()
        async def exec_lua(code: str, timeout: float | None = None) -> str:
            """Execute arbitrary Lua code in DCS and return the result.

            Args:
                code: Lua source code to execute.
                timeout: Optional per-request timeout in seconds.

            Returns:
                The result string from DCS, or an error message.
            """
            return await self.exec_lua(code, timeout)

        @self.mcp.tool()
        async def get_units() -> list[dict[str, Any]] | dict[str, str]:
            """Return the current DCS unit snapshot.

            Returns:
                List of unit dicts, or a dict with an error key if DCS is not ready.
            """
            return await self.get_units()

        @self.mcp.tool()
        async def spawn_unit(group_def: dict[str, Any]) -> str:
            """Spawn a unit group in DCS.

            Args:
                group_def: DCS group definition dict.

            Returns:
                Result string from DCS, or an error message.
            """
            return await self.spawn_unit(group_def)

        @self.mcp.tool()
        async def spawn(
            type: str,
            position: dict[str, float],
            kind: str = "vehicle",
            coalition: str = "blue",
        ) -> str:
            """Spawn a unit via the capability-aware bridge (no MIST dependency).

            Args:
                type: DCS type name (e.g. ``"Hummer"``).
                position: Location as ``{"lat":.., "lon":..}`` or ``{"x":.., "z":..}``.
                kind: One of ``vehicle``/``ship``/``plane``/``helicopter``.
                coalition: ``"red"``, ``"blue"`` or ``"neutral"``.

            Returns:
                The spawned group name from DCS, or an error message.
            """
            return await self.spawn(type, position, kind, coalition)

        @self.mcp.tool()
        async def get_mission_info() -> str:
            """Return basic mission information (theatre name) from DCS.

            Returns:
                Mission info string, or an error message if DCS is not ready.
            """
            return await self.get_mission_info()

    def run(self) -> None:
        """Start the MCP server on stdio (blocking)."""
        self.mcp.run()
