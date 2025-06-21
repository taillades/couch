"""CLI to start a server."""

import typer

from couch.server import wheelchair

app = typer.Typer()

@app.command()
def run_wheelchair_server(
    host: str = typer.Option(
        "0.0.0.0",
        envvar="HOST",
        help="Host to bind the server to (from HOST env var if not provided)",
    ),
    port: int = typer.Option(
        8000,
        envvar="PORT",
        help="Port to bind the server to (from PORT env var if not provided)",
    ),
    reload: bool = typer.Option(
        False,
        envvar="RELOAD",
        help="Whether to enable auto-reload on code changes (from RELOAD env var if not provided)",
    ),
    serial_port: str = typer.Option(
        None,
        envvar="SERIAL_PORT",
        help="Serial port for the wheelchair controller (from SERIAL_PORT env var if not provided)",
    ),
) -> None:
    """
    Run the wheelchair server.

    The serial port is read from the SERIAL_PORT environment variable if not provided.
    """
    if not serial_port:
        raise RuntimeError("SERIAL_PORT environment variable is not set and no serial_port was provided")
    wheelchair.run_server(serial_port=serial_port, host=host, port=port, reload=reload)

if __name__ == "__main__":
    app()