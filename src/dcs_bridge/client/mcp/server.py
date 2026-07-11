"""MCP server for dcs-client — catalogue-driven, capability-aware (ADR-0005).

The client holds **no domain knowledge**: it proxies the dcs-serve catalogue and
the generic action API. A small, fixed set of tools is exposed regardless of how
many actions/values the catalogue holds (ADR-0005 *Granularity*, *Placement*):

- ``list_catalog`` / ``search_catalog`` / ``describe_action`` — discovery.
- ``run_action`` — the single generic verb executor (``POST /api/action``).
- ``get_units`` / ``capabilities`` — read-only state.
- ``exec_lua`` — raw Lua, gated to ``superuser`` server-side.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from dcs_bridge.client.config import ClientConfig

logger = logging.getLogger(__name__)


class DcsMcpServer:
    """Wraps FastMCP and proxies dcs-serve's catalogue + generic action API.

    Each tool method delegates to the dcs-serve REST API via httpx, authenticated
    with a ``Authorization: Bearer <token>`` header. The token's role determines
    which actions succeed (enforced server-side).

    Args:
        config: ClientConfig with host, port and api_key (used as the Bearer token).
    """

    def __init__(self, config: ClientConfig) -> None:
        self._base_url = f"http://{config.host}:{config.port}"
        self._headers = {"Authorization": f"Bearer {config.api_key}"}
        self.mcp = FastMCP("dcs-bridge")
        self._register_tools()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET a dcs-serve endpoint, returning parsed JSON or an error dict."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base_url}{path}", headers=self._headers, params=params)
        return self._unwrap(resp)

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        """POST to a dcs-serve endpoint, returning parsed JSON or an error dict."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self._base_url}{path}", json=body, headers=self._headers)
        return self._unwrap(resp)

    @staticmethod
    def _unwrap(resp: httpx.Response) -> Any:
        """Return the JSON body, or a structured error dict for a non-200 status."""
        if resp.status_code != 200:
            detail: Any = resp.status_code
            try:
                detail = resp.json().get("error", detail)
            except (ValueError, AttributeError):
                pass
            return {"error": f"dcs-serve returned {resp.status_code}: {detail}"}
        return resp.json()

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def list_catalog(self) -> Any:
        """Return the actions available for the running mission's capabilities."""
        return await self._get("/api/catalog")

    async def search_catalog(self, query: str) -> Any:
        """Search actions and long-tail parameter values for a query string."""
        return await self._get("/api/catalog/search", params={"q": query})

    async def describe_action(self, name: str) -> Any:
        """Describe one action and resolve its long-tail parameter values."""
        return await self._get(f"/api/catalog/{name}")

    async def run_action(self, name: str, args: dict[str, Any] | None = None, backend: str | None = None) -> str:
        """Perform a high-level semantic action via the generic action API.

        Args:
            name: The verb (see ``list_catalog``/``search_catalog``).
            args: The verb's arguments.
            backend: Optional backend override (debug/repro).

        Returns:
            The action result string, or an error message.
        """
        body: dict[str, Any] = {"name": name, "args": args or {}}
        if backend is not None:
            body["backend"] = backend
        data = await self._post("/api/action", body)
        if isinstance(data, dict) and "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", "")) if isinstance(data, dict) else str(data)

    async def get_units(self) -> Any:
        """Return the current unit snapshot from DCS."""
        return await self._get("/api/units")

    async def capabilities(self) -> Any:
        """Return the frameworks detected in the running mission."""
        return await self._get("/api/capabilities")

    async def exec_lua(self, code: str, timeout: float | None = None) -> str:
        """Execute arbitrary Lua code in DCS (requires the ``superuser`` role).

        Args:
            code: Lua source code to execute.
            timeout: Optional per-request timeout in seconds.

        Returns:
            The result string from DCS, or an error message.
        """
        body: dict[str, Any] = {"code": code}
        if timeout is not None:
            body["timeout"] = timeout
        data = await self._post("/api/exec", body)
        if isinstance(data, dict) and "error" in data:
            return f"Error: {data['error']}"
        return str(data.get("result", "")) if isinstance(data, dict) else str(data)

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register the fixed set of tools with the FastMCP instance."""

        @self.mcp.tool()
        async def list_catalog() -> Any:
            """List the semantic actions available for the running mission."""
            return await self.list_catalog()

        @self.mcp.tool()
        async def search_catalog(query: str) -> Any:
            """Search actions and long-tail values (e.g. DCS types, VEAF keyphrases)."""
            return await self.search_catalog(query)

        @self.mcp.tool()
        async def describe_action(name: str) -> Any:
            """Describe one action's parameters and valid long-tail values."""
            return await self.describe_action(name)

        @self.mcp.tool()
        async def run_action(name: str, args: dict[str, Any] | None = None, backend: str | None = None) -> str:
            """Perform a semantic action (e.g. spawn, smoke, remove, run_keyphrase)."""
            return await self.run_action(name, args, backend)

        @self.mcp.tool()
        async def get_units() -> Any:
            """Return the current DCS unit snapshot."""
            return await self.get_units()

        @self.mcp.tool()
        async def capabilities() -> Any:
            """Return the frameworks detected in the running mission."""
            return await self.capabilities()

        @self.mcp.tool()
        async def exec_lua(code: str, timeout: float | None = None) -> str:
            """Execute arbitrary Lua code in DCS (requires the superuser role)."""
            return await self.exec_lua(code, timeout)

    def run(self) -> None:
        """Start the MCP server on stdio (blocking)."""
        self.mcp.run()
