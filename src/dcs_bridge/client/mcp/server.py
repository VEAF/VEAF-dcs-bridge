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
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from dcs_bridge.client.config import ClientConfig

logger = logging.getLogger(__name__)

# The client must outlast dcs-serve's own patience. dcs-serve waits up to
# ``ServeConfig.default_timeout`` (10 s) for DCS to answer, so httpx's 5 s default made
# the *client* abort first and report a timeout that blamed DCS for a client-side cutoff.
# Letting the server's own 504 arrive gives the authoritative answer (LOT-017 #02).
_HTTP_TIMEOUT_SECONDS = 30.0

# Added on top of a caller-supplied timeout, so ``exec_lua(code, timeout=T)`` actually
# grants the server T seconds instead of being cut short here.
_TIMEOUT_MARGIN_SECONDS = 10.0

# What the user should *do* about each status. dcs-serve's own message says what happened;
# these say which knob to turn. 401 and 403 are deliberately different advice: a 403 means
# the credential is fine and only the role is short, so re-checking the key wastes time.
_STATUS_HINTS: Mapping[int, str] = {
    400: "the arguments were rejected; call describe_action to check this action's parameters",
    401: (
        "the token was not accepted; it must match an entry in dcs-serve's dcs-tokens.yaml, "
        "or the legacy api_key in dcs-serve.yaml"
    ),
    403: (
        "the token is valid but its role is too low for this action; a different key will not "
        "help, you need one with a higher role"
    ),
    404: "no such action or endpoint; call list_catalog to see what this mission supports",
    502: "DCS is not ready; dcs-serve cannot reach the mission",
    503: "DCS is not ready; the mission is not connected to dcs-serve, or its snapshot is stale",
    504: "DCS did not answer in time; retry, or pass a larger timeout",
}


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
        self._target = f"{config.host}:{config.port}"
        self._headers = {"Authorization": f"Bearer {config.api_key}"}
        self.mcp = FastMCP("dcs-bridge")
        self._register_tools()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET a dcs-serve endpoint, returning parsed JSON or an error dict."""

        async def call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.get(f"{self._base_url}{path}", headers=self._headers, params=params)

        return await self._send(call, _HTTP_TIMEOUT_SECONDS)

    async def _post(self, path: str, body: dict[str, Any], timeout: float | None = None) -> Any:
        """POST to a dcs-serve endpoint, returning parsed JSON or an error dict.

        Args:
            path: Endpoint path.
            body: JSON body.
            timeout: The server-side timeout the caller asked for, if any. The client waits
                longer than this so the server's verdict is what surfaces.
        """

        async def call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(f"{self._base_url}{path}", json=body, headers=self._headers)

        budget = _HTTP_TIMEOUT_SECONDS if timeout is None else timeout + _TIMEOUT_MARGIN_SECONDS
        return await self._send(call, max(budget, _HTTP_TIMEOUT_SECONDS))

    async def _send(
        self,
        call: Callable[[httpx.AsyncClient], Awaitable[httpx.Response]],
        timeout: float,
    ) -> Any:
        """Run an HTTP call, converting transport failures into an error dict.

        Without this, a dcs-serve that is simply not running surfaces a raw httpx
        exception to the MCP client instead of something a user can act on.

        Args:
            call: Performs the request on a provided client.
            timeout: Client-side timeout in seconds.

        Returns:
            The parsed JSON body, or ``{"error": <message>}``.
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await call(client)
        except httpx.TimeoutException:
            logger.warning("dcs-serve at %s did not answer within %gs", self._target, timeout)
            return {
                "error": (
                    f"timed out after {timeout:g}s waiting for dcs-serve at {self._target} — "
                    "it is reachable but did not answer; DCS may be busy"
                )
            }
        except httpx.RequestError as exc:
            logger.warning("cannot reach dcs-serve at %s: %s", self._target, exc)
            return {
                "error": (
                    f"cannot reach dcs-serve at {self._target} ({type(exc).__name__}) — check that it "
                    "is running and that host/port in dcs-client.yaml point at it"
                )
            }
        return self._unwrap(resp)

    @staticmethod
    def _server_detail(resp: httpx.Response) -> str | None:
        """Extract dcs-serve's own explanation from an error body.

        dcs-serve uses two shapes, and reading only one silently discards half the
        diagnostics: FastAPI's ``{"detail": ...}`` for the auth dependencies (401, and 403
        from ``require_role``), and ``{"error": ...}`` for the hand-rolled ``JSONResponse``
        paths (400, 403 in ``/api/action``, 404, 504). A 503 carries ``{"ready": false}``
        with no message at all.

        Args:
            resp: The non-200 response.

        Returns:
            The server's message, or None if the body carries none.
        """
        try:
            body = resp.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None
        for key in ("detail", "error"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @classmethod
    def _error_message(cls, resp: httpx.Response) -> str:
        """Build an actionable message: what happened, then what to do about it.

        Args:
            resp: The non-200 response.

        Returns:
            A single-line message combining the status, the server's own explanation when
            it provides one, and the fix for that status.
        """
        message = f"dcs-serve returned {resp.status_code}"
        detail = cls._server_detail(resp)
        if detail:
            message += f" ({detail})"
        hint = _STATUS_HINTS.get(resp.status_code)
        if hint:
            message += f" — {hint}"
        return message

    @classmethod
    def _unwrap(cls, resp: httpx.Response) -> Any:
        """Return the JSON body, or a structured error dict for a non-200 status."""
        if resp.status_code != 200:
            return {"error": cls._error_message(resp)}
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
        data = await self._post("/api/exec", body, timeout=timeout)
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
