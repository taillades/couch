"""CLI to start a server."""

import typer

from couch.server import controller, joystick, wheelchair, main

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
        raise RuntimeError(
            "SERIAL_PORT environment variable is not set and no serial_port was provided"
        )
    wheelchair.run_server(
        serial_port=serial_port,
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def run_controller_server(
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
    left_wheelchair_url: str = typer.Option(
        None,
        envvar="LEFT_WHEELCHAIR_URL",
        help="URL of the left wheelchair (from LEFT_WHEELCHAIR_URL env var if not provided)",
    ),
    right_wheelchair_url: str = typer.Option(
        None,
        envvar="RIGHT_WHEELCHAIR_URL",
        help="URL of the right wheelchair (from RIGHT_WHEELCHAIR_URL env var if not provided)",
    ),
    distance_between_wheelchairs: float = typer.Option(
        None,
        envvar="DISTANCE_BETWEEN_WHEELCHAIRS",
        help="Distance between left and right wheelchairs (from DISTANCE_BETWEEN_WHEELCHAIRS env var if not provided)",
    ),
) -> None:
    """Run the differential wheelchair server."""
    if not left_wheelchair_url:
        raise RuntimeError(
            "LEFT_WHEELCHAIR_URL environment variable is not set and no left_wheelchair_url was provided"
        )
    if not right_wheelchair_url:
        raise RuntimeError(
            "RIGHT_WHEELCHAIR_URL environment variable is not set and no right_wheelchair_url was provided"
        )

    controller.run_server(
        left_wheelchair_url=left_wheelchair_url,
        right_wheelchair_url=right_wheelchair_url,
        distance_between_wheelchairs=distance_between_wheelchairs,
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def run_joystick_server(
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
) -> None:
    """Run the joystick server."""
    joystick.run_server(host=host, port=port, reload=reload)
    
@app.command()
def run_main_server(
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
    joystick_server_url: str = typer.Option(
        None,
        envvar="JOYSTICK_SERVER_URL",
        help="URL of the joystick server (from JOYSTICK_SERVER_URL env var if not provided)",
    ),
    controller_server_url: str = typer.Option(
        None,
        envvar="CONTROLLER_SERVER_URL",
        help="URL of the controller server (from CONTROLLER_SERVER_URL env var if not provided)",
    ),
    update_rate: float = typer.Option(
        None,
        envvar="UPDATE_RATE",
        help="Update rate in Hz for the control loop (from UPDATE_RATE env var if not provided)",
    ),
    deadzone: float = typer.Option(
        None,
        envvar="DEADZONE",
        help="Minimum joystick value to register as input (from DEADZONE env var if not provided)",
    ),
) -> None:
    """Run the main control server that coordinates joystick input and wheelchair control."""
    main.run_server(
        host=host,
        port=port,
        joystick_server_url=joystick_server_url,
        controller_server_url=controller_server_url,
        update_rate=update_rate,
        deadzone=deadzone,
    )

if __name__ == "__main__":
    app()
