"""dcs-serve entry point."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
import uvicorn

from dcs_bridge.serve.api import create_app
from dcs_bridge.serve.capabilities import CapabilityState
from dcs_bridge.serve.config import ServeConfig, load_config
from dcs_bridge.serve.core import CommandBus, DcsConnection, EventBroadcaster, Snapshot, run_tcp_server
from dcs_bridge.serve.security import TicketStore, build_token_store, load_tokens

logger = logging.getLogger(__name__)

_cli = typer.Typer()


@_cli.command()
def _command(
    config: Path = typer.Option(default="dcs-serve.yaml", help="Path to config file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Start the dcs-serve bridge server."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    cfg = load_config(config)
    asyncio.run(_serve(cfg))


def main() -> None:
    """Entry point for dcs-serve."""
    _cli()


async def _serve(cfg: ServeConfig) -> None:
    """Run TCP server and HTTP server concurrently.

    Args:
        cfg: Runtime configuration.
    """
    snapshot = Snapshot()
    bus = CommandBus()
    conn = DcsConnection()
    broadcaster = EventBroadcaster()
    capabilities = CapabilityState()
    tokens = build_token_store(tokens=load_tokens(Path(cfg.tokens_file)), legacy_api_key=cfg.api_key)
    tickets = TicketStore()

    app = create_app(
        snapshot=snapshot,
        bus=bus,
        conn=conn,
        broadcaster=broadcaster,
        config=cfg,
        capabilities=capabilities,
        tokens=tokens,
        tickets=tickets,
    )

    tcp_task = asyncio.create_task(
        run_tcp_server(
            cfg.tcp_host,
            cfg.tcp_port,
            snapshot=snapshot,
            bus=bus,
            conn=conn,
            broadcaster=broadcaster,
            capabilities=capabilities,
        )
    )

    uv_config = uvicorn.Config(app, host=cfg.http_host, port=cfg.http_port, log_level="info")
    server = uvicorn.Server(uv_config)
    http_task = asyncio.create_task(server.serve())

    await asyncio.gather(tcp_task, http_task)


if __name__ == "__main__":
    # PyInstaller bundles this file as the script, so it must invoke the entry
    # point itself (the `dcs-serve = ...:main` console-script does it for Poetry).
    main()
