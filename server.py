from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from libs import differential, models, shark, xbox


class ControllerServer:
    """Unified server that embeds joystick reading, differential control and direct wheelchair commands."""

    def __init__(
        self,
        *,
        left_serial_port: str,
        right_serial_port: str,
        distance_between_wheelchairs: float,
        deadzone: float,
        max_idle_time: float,
        max_speed: float,
        max_direction: float,
    ) -> None:
        """Build the unified server.

        :param left_serial_port: Serial port for the left wheelchair controller
        :param right_serial_port: Serial port for the right wheelchair controller
        :param distance_between_wheelchairs: Center-to-center distance between wheelchairs (in meters)
        :param deadzone: Ignore absolute joystick values below this threshold
        :param max_idle_time: Reset wheelchairs to idle if no commands were issued for that long (seconds)
        :param max_speed: Maximum speed for the wheelchairs (from shark.MAX_SPEED env var if not provided)
        :param max_direction: Maximum direction for the wheelchairs (from shark.MAX_DIRECTION env var if not provided)
        """
        self.left_service = shark.WheelchairController(port=left_serial_port, max_idle_time=max_idle_time)
        self.right_service = shark.WheelchairController(port=right_serial_port, max_idle_time=max_idle_time )

        self.distance_between_wheelchairs = distance_between_wheelchairs
        self.differential_drive = differential.DifferentialDrive(distance_between_wheelchairs, max_speed, max_direction)

        self.remote = xbox.XboxRemote()
        self.deadzone = deadzone
        self.max_speed = max_speed

        self.app = FastAPI(title="Couch Unified Server", version="1.0.0", lifespan=self._lifespan)
        self._setup_routes()

    # ----------------------------- lifespan -----------------------------

    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI):  # noqa: D401
        """Manage application lifespan.

        On startup, the Xbox remote listener and both wheelchair controllers are
        started, and the asynchronous control-loop task is created. On
        shutdown, the control-loop is cancelled **and** the hardware services
        are stopped to free the serial ports.
        """
        self.remote.start()
        self.left_service.start()
        self.right_service.start()
        self._task = asyncio.create_task(self._control_loop())
        yield
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self.remote.stop()
        self.left_service.stop()
        self.right_service.stop()

    # ----------------------------- internal helpers -----------------------------

    def _apply_deadzone(self, value: float) -> float:
        """Return 0 if *value* lies inside the deadzone."""
        return 0.0 if abs(value) < self.deadzone else value

    async def _control_loop(self) -> None:  # noqa: D401
        """Continuously read joystick and command wheelchairs."""
        while True:
            try:
                start_time = time.time()
                speed, direction = self.remote.get_joystick_speed_direction()
                speed = self._apply_deadzone(speed)
                right_cmd, left_cmd = self.differential_drive.calculate_wheelchair_states(speed, direction)
                self.left_service.control(left_cmd.speed, left_cmd.direction)
                self.right_service.control(right_cmd.speed, right_cmd.direction)
                sleep_time = max(0, 0.02 - (time.time() - start_time))
                await asyncio.sleep(sleep_time)
            except Exception as exc:
                print(f"Control-loop error: {exc}")
                await asyncio.sleep(0.02)

    # ----------------------------- routes -----------------------------

    def _setup_routes(self) -> None:
        app = self.app

        # -------- health & root --------
        @app.get("/")
        async def root() -> Dict[str, Any]:  # noqa: D401
            return {
                "message": "Couch Unified Server", 
                "deadzone": self.deadzone,
            }

        @app.get("/health")
        async def health() -> Dict[str, str]:  # noqa: D401
            return {"status": "healthy"}

        # -------- Joystick --------
        @app.get("/joystick", response_model=models.JoystickData)
        async def get_joystick() -> models.JoystickData:  # noqa: D401
            speed, direction = self.remote.get_joystick_speed_direction()
            x, y = self.remote.get_joystick_xy()
            return models.JoystickData(
                speed=speed,
                direction=direction,
                x=x,
                y=y,
                button_a=self.remote.button_a,
                button_b=self.remote.button_b,
                button_x=self.remote.button_x,
                button_y=self.remote.button_y,
                button_up=self.remote.button_up,
                button_down=self.remote.button_down,
                button_left=self.remote.button_left,
                button_right=self.remote.button_right,
                button_start=self.remote.button_start,
            )

        # -------- Wheelchairs direct --------
        @app.post("/wheelchair/left/control")
        async def left_control(cmd: models.WheelchairCommand) -> Dict[str, Any]:  # noqa: D401
            try:
                self.left_service.control(cmd.speed, cmd.direction)
                return {
                    "message": "Left wheelchair command received",
                    "speed": cmd.speed,
                    "direction": cmd.direction,
                }
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        @app.post("/wheelchair/right/control")
        async def right_control(cmd: models.WheelchairCommand) -> Dict[str, Any]:  # noqa: D401
            try:
                self.right_service.control(cmd.speed, cmd.direction)
                return {
                    "message": "Right wheelchair command received",
                    "speed": cmd.speed,
                    "direction": cmd.direction,
                }
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        @app.get("/wheelchair/left/status")
        async def left_status() -> Dict[str, Any]:  # noqa: D401
            return self.left_service.get_status()

        @app.get("/wheelchair/right/status")
        async def right_status() -> Dict[str, Any]:  # noqa: D401
            return self.right_service.get_status()

        # -------- Differential control endpoint --------
        @app.post("/controller/control")
        async def controller_control(cmd: models.WheelchairCommand) -> Dict[str, Any]:  # noqa: D401
            try:
                left_speed, right_speed = self.differential_drive.calculate_wheelchair_states(cmd.speed, cmd.direction)
                self.left_service.control(left_speed, cmd.direction)
                self.right_service.control(right_speed, cmd.direction)
                return {
                    "message": "Couch command received",
                    "speed": cmd.speed,
                    "direction": cmd.direction,
                    "left_speed": left_speed,
                    "right_speed": right_speed,
                }
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        # -------- Dashboard (static HTML) --------
        @app.get("/dashboard", summary="Live controller dashboard")
        async def dashboard() -> FileResponse:  # noqa: D401
            """Return the HTML dashboard for live telemetry."""
            file_path = Path(__file__).resolve().parent / "monitor.html"
            return FileResponse(file_path)

    # ----------------------------- public API -----------------------------

    def run(self, *, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
        """Run the server with Uvicorn."""
        uvicorn.run(self.app, host=host, port=port, reload=reload)


def run_server(
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    left_serial_port: str,
    right_serial_port: str,
    distance_between_wheelchairs: float,
    deadzone: float,
    max_idle_time: float,
    max_speed: float,
    max_direction: float,
    reload: bool = False,
) -> None:
    """Convenience wrapper that instantiates :class:`ControllerServer` and calls :py:meth:`ControllerServer.run`."""
    server = ControllerServer(
        left_serial_port=left_serial_port,
        right_serial_port=right_serial_port,
        distance_between_wheelchairs=distance_between_wheelchairs,
        deadzone=deadzone,
        max_idle_time=max_idle_time,
        max_speed=max_speed,
        max_direction=max_direction,
    )
    server.run(host=host, port=port, reload=reload) 