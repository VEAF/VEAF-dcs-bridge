"""Tests for dcs_bridge.client.mcp.server — catalogue-driven MCP proxy."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dcs_bridge.client.config import ClientConfig
from dcs_bridge.client.mcp.server import DcsMcpServer


def _make_config(**kwargs: Any) -> ClientConfig:
    return ClientConfig(host="127.0.0.1", port=8080, api_key="test-key", **kwargs)


def _mock_response(status_code: int, body: Any) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


def _mock_non_json_response(status_code: int) -> MagicMock:
    """A response whose body is not JSON (e.g. an HTML 500 from a proxy)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.side_effect = ValueError("not json")
    return resp


def _raising_client(exc: Exception, *, method: str = "get") -> Any:
    """Return a patch context manager whose httpx call raises ``exc``."""
    mock_client = AsyncMock()
    setattr(mock_client, method, AsyncMock(side_effect=exc))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("dcs_bridge.client.mcp.server.httpx.AsyncClient"), mock_client


def _patched_client(*, get: MagicMock | None = None, post: MagicMock | None = None) -> Any:
    """Return a patch context manager yielding a mocked httpx.AsyncClient."""
    mock_client = AsyncMock()
    if get is not None:
        mock_client.get = AsyncMock(return_value=get)
    if post is not None:
        mock_client.post = AsyncMock(return_value=post)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    cm = patch("dcs_bridge.client.mcp.server.httpx.AsyncClient")
    return cm, mock_client


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_server_base_url() -> None:
    srv = DcsMcpServer(ClientConfig(host="10.0.0.1", port=9090, api_key="k"))
    assert srv._base_url == "http://10.0.0.1:9090"


def test_server_uses_bearer_token() -> None:
    srv = DcsMcpServer(ClientConfig(host="127.0.0.1", port=8080, api_key="secret"))
    assert srv._headers["Authorization"] == "Bearer secret"


def test_tool_count_is_small_and_fixed() -> None:
    """The MCP tool surface stays small regardless of catalogue size (ADR-0005)."""
    import asyncio

    srv = DcsMcpServer(_make_config())
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "list_catalog",
        "search_catalog",
        "describe_action",
        "run_action",
        "get_units",
        "capabilities",
        "exec_lua",
    }


# ---------------------------------------------------------------------------
# run_action (generic verb executor)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_action_posts_to_action_api() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(200, {"result": "alpha"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.run_action("spawn", {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}})

    assert result == "alpha"
    call = mock_client.post.call_args
    assert call.args[0].endswith("/api/action")
    assert call.kwargs["json"]["name"] == "spawn"
    assert call.kwargs["json"]["args"]["type"] == "Hummer"


@pytest.mark.asyncio
async def test_run_action_includes_backend_when_set() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(200, {"result": "ok"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        await srv.run_action("spawn", {"kind": "farp", "position": {"lat": 1.0, "lon": 2.0}}, backend="ctld")

    assert mock_client.post.call_args.kwargs["json"]["backend"] == "ctld"


@pytest.mark.asyncio
async def test_run_action_surfaces_error() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(403, {"error": "role observer below required operator"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.run_action("spawn", {"type": "X", "position": {"lat": 1.0, "lon": 2.0}})

    assert "operator" in result


# ---------------------------------------------------------------------------
# Discovery + read-only tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_catalog() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, {"actions": [{"name": "spawn"}]}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.list_catalog()

    assert result["actions"][0]["name"] == "spawn"
    assert mock_client.get.call_args.args[0].endswith("/api/catalog")


@pytest.mark.asyncio
async def test_search_catalog_passes_query() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, {"actions": [], "values": []}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        await srv.search_catalog("tank")

    assert mock_client.get.call_args.kwargs["params"] == {"q": "tank"}


@pytest.mark.asyncio
async def test_describe_action() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, {"action": {"name": "spawn"}, "values": {}}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.describe_action("spawn")

    assert result["action"]["name"] == "spawn"
    assert mock_client.get.call_args.args[0].endswith("/api/catalog/spawn")


@pytest.mark.asyncio
async def test_get_units_returns_list() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, [{"name": "Viper-1"}]))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert result[0]["name"] == "Viper-1"


@pytest.mark.asyncio
async def test_get_units_error_on_non_200() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(503, {"ready": False}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict) and "error" in result


@pytest.mark.asyncio
async def test_capabilities() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, {"connected": True, "frameworks": {}}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.capabilities()

    assert result["connected"] is True


# ---------------------------------------------------------------------------
# exec_lua (superuser)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exec_lua_returns_result() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(200, {"result": "42"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.exec_lua("return 42")

    assert result == "42"
    assert mock_client.post.call_args.args[0].endswith("/api/exec")


@pytest.mark.asyncio
async def test_exec_lua_forbidden_surfaces_error() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(403, {"error": "role operator below required superuser"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.exec_lua("return 1")

    assert "superuser" in result


# ---------------------------------------------------------------------------
# Error messages — LOT-017 ticket 01
#
# dcs-serve reports errors in two body shapes: FastAPI's ``{"detail": ...}`` for
# the auth dependencies, and ``{"error": ...}`` for the hand-rolled JSONResponse
# paths. Both must reach the user, and 401 (bad credential) must not be conflated
# with 403 (valid credential, insufficient role) — they need opposite fixes.
# ---------------------------------------------------------------------------


async def _get_error(status: int, body: Any) -> str:
    """Drive a read-only tool to its error string for the given response."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(status, body))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()
    assert isinstance(result, dict), f"expected an error dict, got {result!r}"
    return str(result["error"])


@pytest.mark.asyncio
async def test_401_names_the_credential_and_keeps_server_detail() -> None:
    """A 401 must point at the token, and not be reported as a DCS problem."""
    msg = await _get_error(401, {"detail": "Invalid or missing token"})

    assert "401" in msg
    # The server's own explanation lives in `detail` and must not be discarded.
    assert "Invalid or missing token" in msg
    assert "dcs-tokens.yaml" in msg
    assert "DCS not ready" not in msg
    assert "not connected" not in msg


@pytest.mark.asyncio
async def test_403_blames_the_role_not_the_credential() -> None:
    """A 403 means the token is valid but under-privileged — a different fix."""
    msg = await _get_error(403, {"detail": "role observer below required operator"})

    assert "role observer below required operator" in msg
    assert "role" in msg.lower()
    # Telling the user to check their key here would send them down the wrong path.
    assert "dcs-tokens.yaml" not in msg


@pytest.mark.asyncio
async def test_403_from_action_api_uses_the_error_key() -> None:
    """/api/action reports the same failure under `error` rather than `detail`."""
    msg = await _get_error(403, {"error": "role observer below required operator"})

    assert "role observer below required operator" in msg
    assert "role" in msg.lower()


@pytest.mark.asyncio
async def test_503_still_reports_dcs_not_ready() -> None:
    """503 carries no message from the server, so the hint must supply one."""
    msg = await _get_error(503, {"ready": False})

    assert "503" in msg
    assert "DCS" in msg


@pytest.mark.asyncio
async def test_504_is_identified_as_a_timeout() -> None:
    msg = await _get_error(504, {"error": "timeout"})

    assert "504" in msg
    assert "timeout" in msg.lower()


@pytest.mark.asyncio
async def test_404_points_at_the_catalogue() -> None:
    msg = await _get_error(404, {"error": "unknown action: teleport"})

    assert "unknown action: teleport" in msg
    assert "list_catalog" in msg


@pytest.mark.asyncio
async def test_400_points_at_describe_action() -> None:
    msg = await _get_error(400, {"error": "spawn: missing required arg 'position'"})

    assert "missing required arg" in msg
    assert "describe_action" in msg


@pytest.mark.asyncio
async def test_status_code_is_not_repeated() -> None:
    """The old message read 'dcs-serve returned 401: 401' — status twice, no advice."""
    msg = await _get_error(401, {"detail": "Invalid or missing token"})

    assert msg.count("401") == 1


@pytest.mark.asyncio
async def test_non_json_error_body_degrades_gracefully() -> None:
    """An HTML/empty body must not raise while building the message."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_non_json_response(500))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "500" in result["error"]


# ---------------------------------------------------------------------------
# Unreachable dcs-serve — no raw exception may reach the MCP client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_error_returns_message_not_exception() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.ConnectError("refused"))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "cannot reach dcs-serve" in result["error"]
    assert "127.0.0.1:8080" in result["error"]


@pytest.mark.asyncio
async def test_read_timeout_says_the_connection_was_established() -> None:
    """A read timeout means the server *is* there and simply did not answer."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.ReadTimeout("too slow"))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "timed out" in result["error"].lower()
    assert "127.0.0.1:8080" in result["error"]
    assert "may be busy" in result["error"]
    assert "never established" not in result["error"]


@pytest.mark.asyncio
async def test_connect_timeout_does_not_claim_the_server_was_reachable() -> None:
    """`ConnectTimeout` is a `TimeoutException` too, but nothing was ever reached.

    Claiming "reachable but did not answer" here would misattribute a down host or a
    wrong port — the exact failure mode this lot exists to remove.
    """
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.ConnectTimeout("no route"))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "timed out" in result["error"].lower()
    assert "never established" in result["error"]
    assert "may be busy" not in result["error"]


@pytest.mark.asyncio
async def test_pool_timeout_is_reported_as_a_client_side_limit() -> None:
    """`PoolTimeout` says nothing about dcs-serve, so it must not blame it."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.PoolTimeout("no slot"))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "client-side" in result["error"]
    assert "not a dcs-serve problem" in result["error"]


@pytest.mark.asyncio
async def test_connect_error_keeps_string_return_type_for_run_action() -> None:
    """run_action's contract is a string, including when the server is down."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.ConnectError("refused"), method="post")
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.run_action("spawn", {"type": "X"})

    assert isinstance(result, str)
    assert "cannot reach dcs-serve" in result


@pytest.mark.asyncio
async def test_connect_error_keeps_string_return_type_for_exec_lua() -> None:
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _raising_client(httpx.ConnectError("refused"), method="post")
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        result = await srv.exec_lua("return 1")

    assert isinstance(result, str)
    assert "cannot reach dcs-serve" in result


# ---------------------------------------------------------------------------
# Client timeout must outlast the server's — LOT-017 ticket 02
#
# httpx defaults to 5 s while ServeConfig.default_timeout is 10 s, so the client
# used to abort first and report a timeout that blamed DCS for a client-side
# cutoff. The server's own 504 is the authoritative answer, so it must fire first.
# ---------------------------------------------------------------------------


def _client_timeout_seconds(mock_cls: MagicMock) -> float:
    """Read the timeout httpx.AsyncClient was constructed with."""
    timeout = mock_cls.call_args.kwargs["timeout"]
    return float(timeout.read if isinstance(timeout, httpx.Timeout) else timeout)


@pytest.mark.asyncio
async def test_client_timeout_outlasts_server_default() -> None:
    from dcs_bridge.serve.config import ServeConfig

    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(get=_mock_response(200, []))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        await srv.get_units()

    assert _client_timeout_seconds(mock_cls) > ServeConfig().default_timeout


@pytest.mark.asyncio
async def test_client_timeout_follows_an_explicit_exec_timeout() -> None:
    """exec_lua(timeout=T) is useless if the client hangs up before T elapses."""
    srv = DcsMcpServer(_make_config())
    cm, mock_client = _patched_client(post=_mock_response(200, {"result": "ok"}))
    with cm as mock_cls:
        mock_cls.return_value = mock_client
        await srv.exec_lua("return 1", timeout=120.0)

    assert _client_timeout_seconds(mock_cls) > 120.0
