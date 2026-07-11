"""Tests for dcs_bridge.client.mcp.server — catalogue-driven MCP proxy."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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
