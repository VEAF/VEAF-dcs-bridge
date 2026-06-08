"""dcs-client entry point."""

from __future__ import annotations

from pathlib import Path

import typer

from dcs_bridge.client.config import load_config

app = typer.Typer(help="dcs-bridge client — TUI, MCP and web interfaces.")


@app.command()
def tui(
    config: Path = typer.Option(Path("dcs-client.yaml"), "--config", "-c", help="Path to dcs-client.yaml"),
) -> None:
    """Launch the interactive TUI (Textual terminal UI)."""
    from dcs_bridge.client.tui.app import DcsBridgeApp

    cfg = load_config(config)
    DcsBridgeApp(cfg).run()


@app.command()
def mcp(
    config: Path = typer.Option(Path("dcs-client.yaml"), "--config", "-c", help="Path to dcs-client.yaml"),
) -> None:
    """Launch the MCP server (stdio transport) exposing dcs-serve tools to AI agents."""
    from dcs_bridge.client.mcp.server import DcsMcpServer

    cfg = load_config(config)
    DcsMcpServer(cfg).run()


def main() -> None:
    """Start the dcs-client."""
    app()
