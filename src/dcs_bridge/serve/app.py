"""dcs-serve entry point."""

import typer

app = typer.Typer()


def main() -> None:
    """Start the dcs-serve server."""
    app()
