"""CLI to start a server."""

from dotenv import load_dotenv
import typer
from servers import controller, navigation
import os

app = typer.Typer()

CONFIG_FILE = "config.env"
load_dotenv(CONFIG_FILE)

@app.command()
def main():
    """Run the server and the static server."""
    pass

@app.command()
def run_controller(
    host: str = typer.Option(
        '0.0.0.0',
        envvar="CONTROLLER_HOST",
        help="Host to bind the controller server to (from CONTROLLER_HOST env var if not provided)",
    ),
    port: int = typer.Option(
        '8000',
        envvar="CONTROLLER_PORT",
        help="Port to bind the controller server to (from CONTROLLER_PORT env var if not provided)",
    ),
    left_serial_port: str = typer.Option(
        None,
        envvar="CONTROLLER_LEFT_SERIAL_PORT",
        help="Serial port for the left wheelchair (from CONTROLLER_LEFT_SERIAL_PORT env var if not provided)",
    ),
    right_serial_port: str = typer.Option(
        None,
        envvar="CONTROLLER_RIGHT_SERIAL_PORT",
        help="Serial port for the right wheelchair (from CONTROLLER_RIGHT_SERIAL_PORT env var if not provided)",
    ),
    lights_serial_port: str = typer.Option(
        None,
        envvar="CONTROLLER_LIGHT_SERIAL_PORT",
        help="Serial port for the lights (from CONTROLLER_LIGHT_SERIAL_PORT env var if not provided)",
    ),
    deadzone: float = typer.Option(
        '0.1',
        envvar="CONTROLLER_DEADZONE",
        help="Joystick deadzone value (from CONTROLLER_DEADZONE env var if not provided)",
    ),
) -> None:
    """Run the unified Couch server handling joystick, controller and wheelchairs."""

    if not left_serial_port:
        raise RuntimeError("LEFT_SERIAL_PORT env var not set and no left_serial_port was provided")
    if not right_serial_port:
        raise RuntimeError("RIGHT_SERIAL_PORT env var not set and no right_serial_port was provided")

    controller.run_server(
        host=host,
        port=port,
        left_serial_port=left_serial_port,
        right_serial_port=right_serial_port,
        lights_serial_port=lights_serial_port,
        deadzone=deadzone,
    )
    

@app.command()
def run_navigation(
    host: str = typer.Option(
        '0.0.0.0',
        envvar="NAVIGATION_HOST",
        help="Host to bind the navigation server to (from NAVIGATION_HOST env var if not provided)",
    ),
    port: int = typer.Option(
        '8080',
        envvar="NAVIGATION_PORT",
        help="Port to bind the navigation server to (from NAVIGATION_PORT env var if not provided)",
    ),
    controller_host: str = typer.Option(
        None,
        envvar="CONTROLLER_HOST",
        help="Host of the controller server (from CONTROLLER_HOST env var if not provided)",
    ),
    controller_port: int = typer.Option(
        None,
        envvar="CONTROLLER_PORT",
        help="Port of the controller server (from CONTROLLER_PORT env var if not provided)",
    ),
    thermo_serial_port: str = typer.Option(
        None,
        envvar="NAVIGATION_THERMO_SERIAL_PORT",
        help="Serial port for the temperature sensor (from NAVIGATION_THERMO_SERIAL_PORT env var if not provided)",
    ),
    gps_serial_port: str = typer.Option(
        None,
        envvar="NAVIGATION_GPS_SERIAL_PORT",
        help="Serial port for the GPS (from NAVIGATION_GPS_SERIAL_PORT env var if not provided)",
    ),
) -> None:
    """Run the navigation server."""
    if not controller_host:
        raise RuntimeError("CONTROLLER_HOST env var not set and no controller_host was provided")
    if not controller_port:
        raise RuntimeError("CONTROLLER_PORT env var not set and no controller_port was provided")

    navigation.run_server(
        host=host,
        port=port,
        controller_host=controller_host,
        controller_port=controller_port,
        thermo_serial_port=thermo_serial_port,
        gps_serial_port=gps_serial_port,
    )

if __name__ == "__main__":
    app()   
