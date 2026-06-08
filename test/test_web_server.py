"""Tests for the web client server (LOT-008)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dcs_bridge.client.config import ClientConfig, load_config


# ---------------------------------------------------------------------------
# ClientConfig — web_port field
# ---------------------------------------------------------------------------


def test_client_config_web_port_default() -> None:
    cfg = ClientConfig()
    assert cfg.web_port == 8081


def test_client_config_web_port_override() -> None:
    cfg = ClientConfig(web_port=9000)
    assert cfg.web_port == 9000


def test_load_config_web_port_from_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "dcs-client.yaml"
    yaml_file.write_text("host: 10.0.0.1\nport: 8080\napi_key: abc\nweb_port: 9090\n", encoding="utf-8")
    cfg = load_config(yaml_file)
    assert cfg.web_port == 9090


# ---------------------------------------------------------------------------
# run_web — smoke tests (no real server started)
# ---------------------------------------------------------------------------


def test_run_web_constructs_uvicorn_config() -> None:
    """run_web must build a Uvicorn Server and call server.run()."""
    mock_server = MagicMock()
    mock_server.startup = MagicMock(return_value=None)

    with (
        patch("dcs_bridge.client.web.server.uvicorn.Server", return_value=mock_server) as mock_server_cls,
        patch("dcs_bridge.client.web.server.uvicorn.Config") as mock_config_cls,
        patch("dcs_bridge.client.web.server.threading.Thread"),
    ):
        mock_server.run = MagicMock()

        from dcs_bridge.client.web.server import run_web

        run_web("127.0.0.1", 8081)

        mock_config_cls.assert_called_once()
        call_kwargs = mock_config_cls.call_args
        assert call_kwargs.kwargs.get("host") == "127.0.0.1"
        assert call_kwargs.kwargs.get("port") == 8081
        mock_server_cls.assert_called_once()
        mock_server.run.assert_called_once()


def test_run_web_opens_browser_when_ready() -> None:
    """Browser must be opened after the ready_event is set."""
    import threading

    browser_urls: list[str] = []
    ready_event_holder: list[threading.Event] = []

    def capture_thread(target, daemon):  # type: ignore[no-untyped-def]
        # Capture the _open_browser thread's target; store event reference via closure inspection
        thread = MagicMock()
        thread.start = MagicMock()
        return thread

    mock_server = MagicMock()
    mock_server.run = MagicMock()

    original_event = threading.Event()
    original_event.set()  # simulate server ready immediately

    with (
        patch("dcs_bridge.client.web.server.uvicorn.Server", return_value=mock_server),
        patch("dcs_bridge.client.web.server.uvicorn.Config"),
        patch("dcs_bridge.client.web.server.threading.Event", return_value=original_event),
        patch("dcs_bridge.client.web.server.threading.Thread") as mock_thread_cls,
        patch("dcs_bridge.client.web.server.webbrowser.open", side_effect=browser_urls.append),
        patch("dcs_bridge.client.web.server.threading.Timer") as mock_timer_cls,
    ):
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        from importlib import reload
        import dcs_bridge.client.web.server as web_server_module

        reload(web_server_module)
        web_server_module.run_web("127.0.0.1", 8081)

        mock_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# Static file presence
# ---------------------------------------------------------------------------


def test_static_index_html_exists() -> None:
    static_dir = Path(__file__).parent.parent / "src" / "dcs_bridge" / "client" / "web" / "static"
    assert (static_dir / "index.html").exists()


def test_static_index_html_contains_leaflet() -> None:
    static_dir = Path(__file__).parent.parent / "src" / "dcs_bridge" / "client" / "web" / "static"
    content = (static_dir / "index.html").read_text(encoding="utf-8")
    assert "leaflet" in content.lower()
    assert "WebSocket" in content
    assert "full_refresh" in content
    assert "unit_destroyed" in content
    assert "integrity=" in content
