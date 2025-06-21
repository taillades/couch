"""CLI to start a server."""

import typer

from couch.server import wheelchair

app = typer.Typer()

@app.command()
def run(serial_port: str, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the wheelchair server."""
    wheelchair.run_server(serial_port=serial_port, host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()