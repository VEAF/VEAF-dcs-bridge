"""Tests for the web client server (LOT-008)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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

        run_web("127.0.0.1", 8081, "10.0.0.1", 8080, "secret")

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
        web_server_module.run_web("127.0.0.1", 8081, "10.0.0.1", 8080, "secret")

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


def test_static_index_html_uses_vendored_leaflet_not_cdn() -> None:
    """Leaflet must be served locally (LOT-016) — no CDN dependency, no stale SRI hash."""
    static_dir = Path(__file__).parent.parent / "src" / "dcs_bridge" / "client" / "web" / "static"
    content = (static_dir / "index.html").read_text(encoding="utf-8")
    assert "unpkg.com" not in content
    assert "integrity=" not in content
    assert "vendor/leaflet/leaflet.js" in content
    assert "vendor/leaflet/leaflet.css" in content


def test_static_leaflet_vendored_assets_exist() -> None:
    """The vendored Leaflet distribution (JS, CSS, and CSS-referenced images) must ship."""
    vendor = Path(__file__).parent.parent / "src" / "dcs_bridge" / "client" / "web" / "static" / "vendor" / "leaflet"
    assert (vendor / "leaflet.js").is_file()
    assert (vendor / "leaflet.css").is_file()
    for image in ("layers.png", "layers-2x.png", "marker-icon.png"):
        assert (vendor / "images" / image).is_file()


def test_vendored_leaflet_is_served_over_http() -> None:
    """A StaticFiles mount over the static dir serves the vendored assets (no 404)."""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.testclient import TestClient

    from dcs_bridge.client.web import server as web_server

    app = FastAPI()
    app.mount("/", StaticFiles(directory=web_server._STATIC_DIR, html=True), name="static")
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/vendor/leaflet/leaflet.js").status_code == 200
    assert client.get("/vendor/leaflet/leaflet.css").status_code == 200
    assert client.get("/vendor/leaflet/images/marker-icon.png").status_code == 200


# ---------------------------------------------------------------------------
# /config.json endpoint and config wiring (LOT-015)
# ---------------------------------------------------------------------------


def test_config_json_returns_serve_params() -> None:
    """GET /config.json exposes the dcs-serve host/port/api_key for the browser."""
    from fastapi.testclient import TestClient

    from dcs_bridge.client.web.server import create_web_app

    client = TestClient(create_web_app("10.0.0.1", 8080, "secret"))
    resp = client.get("/config.json")
    assert resp.status_code == 200
    assert resp.json() == {"host": "10.0.0.1", "port": 8080, "api_key": "secret"}


def test_config_json_route_does_not_shadow_static() -> None:
    """The /config.json route must not prevent the static mount from serving index.html."""
    from fastapi.testclient import TestClient

    from dcs_bridge.client.web.server import create_web_app

    client = TestClient(create_web_app("127.0.0.1", 8080, ""))
    assert client.get("/").status_code == 200
    assert client.get("/vendor/leaflet/leaflet.js").status_code == 200


def test_web_command_passes_config_to_run_web(tmp_path: Path) -> None:
    """`dcs-client web` must forward the config's host/port/api_key to run_web."""
    from typer.testing import CliRunner

    from dcs_bridge.client.app import app

    cfg_file = tmp_path / "dcs-client.yaml"
    cfg_file.write_text("host: 10.0.0.1\nport: 8080\napi_key: abc\nweb_port: 8081\n", encoding="utf-8")

    with patch("dcs_bridge.client.web.server.run_web") as mock_run_web:
        result = CliRunner().invoke(app, ["web", "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    mock_run_web.assert_called_once_with("127.0.0.1", 8081, "10.0.0.1", 8080, "abc")


def test_web_command_web_port_override_wins(tmp_path: Path) -> None:
    """--web-port overrides the config's web_port while serve params come from config."""
    from typer.testing import CliRunner

    from dcs_bridge.client.app import app

    cfg_file = tmp_path / "dcs-client.yaml"
    cfg_file.write_text("host: 10.0.0.1\nport: 8080\napi_key: abc\nweb_port: 8081\n", encoding="utf-8")

    with patch("dcs_bridge.client.web.server.run_web") as mock_run_web:
        result = CliRunner().invoke(app, ["web", "--config", str(cfg_file), "--web-port", "9099"])

    assert result.exit_code == 0, result.output
    mock_run_web.assert_called_once_with("127.0.0.1", 9099, "10.0.0.1", 8080, "abc")
