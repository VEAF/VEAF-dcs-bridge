"""Tests for dcs_bridge.client.tui.app."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dcs_bridge.client.config import ClientConfig
from dcs_bridge.client.tui.app import _COALITION_LABEL, DcsBridgeApp
from dcs_bridge.common.models import Coalition


def _make_unit(name: str = "Unit1", coalition: int = Coalition.BLUE) -> dict[str, Any]:
    return {
        "name": name,
        "type": "F-16C_50",
        "coalition": coalition,
        "position_geo": {"lat": 41.1234, "lon": 41.5678},
        "altitude_agl": 1500.0,
    }


def _make_app() -> DcsBridgeApp:
    return DcsBridgeApp(ClientConfig(host="127.0.0.1", port=8080, api_key="test-key"))


def test_coalition_labels_cover_all_values() -> None:
    assert Coalition.NEUTRAL in _COALITION_LABEL
    assert Coalition.RED in _COALITION_LABEL
    assert Coalition.BLUE in _COALITION_LABEL


@pytest.mark.asyncio
async def test_update_units_populates_table() -> None:
    app = _make_app()
    async with app.run_test() as pilot:
        from textual.widgets import DataTable

        app._update_units([_make_unit("Alpha", Coalition.BLUE), _make_unit("Bravo", Coalition.RED)])
        table = app.query_one("#units", DataTable)
        assert table.row_count == 2


@pytest.mark.asyncio
async def test_lua_input_calls_http_exec() -> None:
    app = _make_app()
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "42"}

    with patch("dcs_bridge.client.tui.app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async with app.run_test() as pilot:
            from textual.widgets import Input

            input_widget = app.query_one("#lua-input", Input)
            input_widget.value = "return 42"
            await app.on_input_submitted(Input.Submitted(input_widget, "return 42"))
            await pilot.pause()

        # The WS worker also POSTs /api/ws-ticket; isolate the /api/exec call.
        exec_calls = [c for c in mock_client.post.call_args_list if str(c.args[0]).endswith("/api/exec")]
        assert len(exec_calls) == 1
        assert exec_calls[0].kwargs["json"]["code"] == "return 42"


@pytest.mark.asyncio
async def test_url_construction() -> None:
    cfg = ClientConfig(host="192.168.1.10", port=9999, api_key="abc")
    app = DcsBridgeApp(cfg)
    assert app._base_url == "http://192.168.1.10:9999"
    assert app._ws_base == "ws://192.168.1.10:9999/ws/stream"
    # The token is carried as a Bearer header, never in the WS URL.
    assert "abc" not in app._ws_base
    assert app._headers["Authorization"] == "Bearer abc"
