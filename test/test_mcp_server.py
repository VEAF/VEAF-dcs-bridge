"""Tests for dcs_bridge.client.mcp.server."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dcs_bridge.client.config import ClientConfig
from dcs_bridge.client.mcp.server import DcsMcpServer


def _make_config(**kwargs: Any) -> ClientConfig:
    return ClientConfig(host="127.0.0.1", port=8080, api_key="test-key", **kwargs)


def _mock_response(status_code: int, body: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# DcsMcpServer construction
# ---------------------------------------------------------------------------


def test_server_base_url() -> None:
    cfg = ClientConfig(host="10.0.0.1", port=9090, api_key="k")
    srv = DcsMcpServer(cfg)
    assert srv._base_url == "http://10.0.0.1:9090"


def test_server_headers_contain_bearer_token() -> None:
    cfg = ClientConfig(host="127.0.0.1", port=8080, api_key="secret")
    srv = DcsMcpServer(cfg)
    assert srv._headers["Authorization"] == "Bearer secret"


# ---------------------------------------------------------------------------
# exec_lua tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exec_lua_returns_result() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"result": "42"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.exec_lua("return 42")

    assert result == "42"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args.kwargs["json"]["code"] == "return 42"
    assert call_args.kwargs["json"].get("timeout") is None


@pytest.mark.asyncio
async def test_exec_lua_with_timeout() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"result": "ok"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.exec_lua("return 1", timeout=5.0)

    call_args = mock_client.post.call_args
    assert call_args.kwargs["json"]["timeout"] == 5.0
    assert result == "ok"


@pytest.mark.asyncio
async def test_exec_lua_returns_error_message() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"error": "syntax error near '?'"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.exec_lua("???")

    assert "syntax error" in result


@pytest.mark.asyncio
async def test_exec_lua_dcs_not_ready() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(503, {"ready": False})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.exec_lua("return 1")

    assert "503" in result or "not ready" in result.lower()


# ---------------------------------------------------------------------------
# get_units tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_units_returns_list() -> None:
    srv = DcsMcpServer(_make_config())
    units_payload = [
        {
            "name": "Viper-1",
            "type": "F-16C_50",
            "coalition": 2,
            "position_geo": {"lat": 41.1, "lon": 41.5},
            "altitude_agl": 3000.0,
        }
    ]
    mock_resp = _mock_response(200, units_payload)

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.get_units()

    assert isinstance(result, list)
    assert result[0]["name"] == "Viper-1"


@pytest.mark.asyncio
async def test_get_units_dcs_not_ready() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(503, {"ready": False})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.get_units()

    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# spawn_unit tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawn_unit_returns_result() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"result": "spawned"})
    group_def: dict[str, Any] = {"name": "TestGroup", "units": []}

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.spawn_unit(group_def)

    assert result == "spawned"
    call_args = mock_client.post.call_args
    assert call_args.kwargs["json"]["group_def"] == group_def


@pytest.mark.asyncio
async def test_spawn_unit_dcs_error() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"error": "spawn failed"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.spawn_unit({})

    assert "spawn failed" in result


# ---------------------------------------------------------------------------
# spawn (semantic action) tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawn_posts_action_and_returns_group_name() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"result": "alpha"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.spawn("Hummer", {"lat": 43.0, "lon": 1.5}, kind="vehicle", coalition="blue")

    assert result == "alpha"
    call_args = mock_client.post.call_args
    assert call_args.args[0].endswith("/api/action")
    body = call_args.kwargs["json"]
    assert body["name"] == "spawn"
    assert body["args"]["type"] == "Hummer"
    assert body["args"]["position"] == {"lat": 43.0, "lon": 1.5}


@pytest.mark.asyncio
async def test_spawn_reports_error_detail_on_400() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(400, {"error": "unsupported kind: 'submarine'"})
    mock_resp.headers = {"content-type": "application/json"}

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.spawn("X", {"lat": 1.0, "lon": 2.0}, kind="submarine")

    assert "submarine" in result


# ---------------------------------------------------------------------------
# get_mission_info tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_mission_info_returns_result() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(200, {"result": "Caucasus"})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.get_mission_info()

    assert result == "Caucasus"


@pytest.mark.asyncio
async def test_get_mission_info_dcs_not_ready() -> None:
    srv = DcsMcpServer(_make_config())
    mock_resp = _mock_response(503, {"ready": False})

    with patch("dcs_bridge.client.mcp.server.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await srv.get_mission_info()

    assert "503" in result or "not ready" in result.lower()
