"""CLI to start a server."""

from dotenv import load_dotenv
import typer
import server
import os

app = typer.Typer()

CONFIG_FILE = "config.env"
load_dotenv(CONFIG_FILE)

@app.command()
def run(
    host: str = typer.Option(
        '0.0.0.0',
        envvar="HOST",
        help="Host to bind the server to (from HOST env var if not provided)",
    ),
    port: int = typer.Option(
        '8000',
        envvar="PORT",
        help="Port to bind the server to (from PORT env var if not provided)",
    ),
    left_serial_port: str = typer.Option(
        None,
        envvar="LEFT_SERIAL_PORT",
        help="Serial port for the left wheelchair (from LEFT_SERIAL_PORT env var if not provided)",
    ),
    right_serial_port: str = typer.Option(
        None,
        envvar="RIGHT_SERIAL_PORT",
        help="Serial port for the right wheelchair (from RIGHT_SERIAL_PORT env var if not provided)",
    ),
    deadzone: float = typer.Option(
        '0.1',
        envvar="DEADZONE",
        help="Joystick deadzone value (from DEADZONE env var if not provided)",
    ),
    reload: bool = typer.Option(
        False,
        envvar="RELOAD",
        help="Reload on code changes (from RELOAD env var if not provided)",
    ),
) -> None:
    """Run the unified Couch server handling joystick, controller and wheelchairs."""

    if not left_serial_port:
        raise RuntimeError("LEFT_SERIAL_PORT env var not set and no left_serial_port was provided")
    if not right_serial_port:
        raise RuntimeError("RIGHT_SERIAL_PORT env var not set and no right_serial_port was provided")

    server.run_server(
        host=host,
        port=port,
        left_serial_port=left_serial_port,
        right_serial_port=right_serial_port,
        deadzone=deadzone,
        reload=reload,
    )

if __name__ == "__main__":
    app()
