"""dcs-client entry point."""

from __future__ import annotations

from pathlib import Path

import typer

from dcs_bridge.client.config import load_config

app = typer.Typer(help="dcs-bridge client — TUI, MCP and web interfaces.")


@app.command()
def tui(
    config: Path = typer.Option(default="dcs-client.yaml", help="Path to dcs-client.yaml"),
) -> None:
    """Launch the interactive TUI (Textual terminal UI)."""
    from dcs_bridge.client.tui.app import DcsBridgeApp

    cfg = load_config(config)
    DcsBridgeApp(cfg).run()


@app.command()
def web(
    config: Path = typer.Option(default="dcs-client.yaml", help="Path to dcs-client.yaml"),
    web_host: str = typer.Option("127.0.0.1", "--web-host", help="Bind address for the local HTTP server"),
    web_port: int = typer.Option(0, "--web-port", help="Port for the local HTTP server (0 = use config value)"),
) -> None:
    """Launch the web client (Leaflet map) and open the browser."""
    from dcs_bridge.client.web.server import run_web

    cfg = load_config(config)
    effective_port = web_port if web_port else cfg.web_port
    run_web(web_host, effective_port, cfg.host, cfg.port, cfg.api_key)


@app.command()
def mcp(
    config: Path = typer.Option(default="dcs-client.yaml", help="Path to dcs-client.yaml"),
) -> None:
    """Launch the MCP server (stdio transport) exposing dcs-serve tools to AI agents."""
    from dcs_bridge.client.mcp.server import DcsMcpServer

    cfg = load_config(config)
    DcsMcpServer(cfg).run()


def main() -> None:
    """Start the dcs-client."""
    app()


if __name__ == "__main__":
    # PyInstaller bundles this file as the script, so it must invoke the entry
    # point itself (the `dcs-client = ...:main` console-script does it for Poetry).
    main()
