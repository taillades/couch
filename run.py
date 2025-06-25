"""CLI to start a server."""

from dotenv import load_dotenv
import typer
import server

app = typer.Typer()

CONFIG_FILE = "config.env"
load_dotenv(CONFIG_FILE)

@app.command()
def run_big_server(
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
    distance_between_wheelchairs: float = typer.Option(
        1.01,
        envvar="DISTANCE_BETWEEN_WHEELCHAIRS",
        help="Distance between wheelchairs in meters (from DISTANCE_BETWEEN_WHEELCHAIRS env var if not provided)",
    ),
    deadzone: float = typer.Option(
        0.1,
        envvar="DEADZONE",
        help="Joystick deadzone value (from DEADZONE env var if not provided)",
    ),
    max_idle_time: float = typer.Option(
        1.0,
        envvar="MAX_IDLE_TIME",
        help="Maximum idle time for wheelchair controllers (from MAX_IDLE_TIME env var if not provided)",
    ),
    max_speed: float =   typer.Option(
        1.0,
        envvar="MAX_SPEED",
        help="Maximum speed for the wheelchairs (from MAX_SPEED env var if not provided)",
    ),
    max_direction: float = typer.Option(
        0.2,
        envvar="MAX_DIRECTION",
        help="Maximum direction for the wheelchairs (from MAX_DIRECTION env var if not provided)",
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
        distance_between_wheelchairs=distance_between_wheelchairs,
        deadzone=deadzone,
        max_idle_time=max_idle_time,
        max_speed=max_speed,
        max_direction=max_direction,    
        reload=reload,
    )

if __name__ == "__main__":
    app()
