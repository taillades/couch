from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import math
from typing import Any, Dict
import time
import os

from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from libs import differential, models, shark, speaker, xbox

STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")

class ControllerServer:
    """Unified server that embeds joystick reading, differential control and direct wheelchair commands."""

    def __init__(
        self,
        *,
        left_serial_port: str,
        right_serial_port: str,
        deadzone: float,
        play_intro: bool,
    ) -> None:
        """Build the unified server.

        :param left_serial_port: Serial port for the left wheelchair controller
        :param right_serial_port: Serial port for the right wheelchair controller
        :param deadzone: Ignore absolute joystick values below this threshold
        :param play_intro: Play the intro music
        """
        self.left_service = shark.WheelchairController(port=left_serial_port)
        self.right_service = shark.WheelchairController(port=right_serial_port)
        self.differential_drive = differential.DifferentialDrive()
        self.play_intro = play_intro
        
        self.target_geopoint: models.Geopoint | None = None
        self.geoposition: models.Geopoint | None = None
        # TODO(taillades): remove this once we have a GPS
        self.geoposition = models.Geopoint(lat=40.7865, lon=-119.2065)
        self.theta = 45 / 180 * math.pi
        self.remote = xbox.XboxRemote()
        self.deadzone = deadzone
        
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
        if self.play_intro:
            try:
                speaker.play_music('ff7_victory')
            except Exception as exc:
                print(f"Error playing music: {exc}")
                pass
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
                direction = self._apply_deadzone(direction)
                right_cmd, left_cmd = self.differential_drive.calculate_wheelchair_states(speed, direction)
                self.left_service.control(left_cmd.speed, left_cmd.direction)
                self.right_service.control(right_cmd.speed, right_cmd.direction)
                sleep_time = max(0, 0.02 - (time.time() - start_time))
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                # Task cancellation: exit the loop gracefully
                print("Control-loop crashed")
                break
            except Exception as exc:
                print(f"Control-loop error: {exc}")
                await asyncio.sleep(0.02)

    # ----------------------------- routes -----------------------------

    def _setup_routes(self) -> None:
        app = self.app

        # -------- static files --------
        app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")
        app.mount("/js", StaticFiles(directory=os.path.join(STATIC_PATH, "js")), name="js")
        app.mount("/burning_man_2023_geojson", StaticFiles(directory=os.path.join(STATIC_PATH, "burning_man_2023_geojson")), name="geojson")
        app.mount("/tiles", StaticFiles(directory=os.path.join(STATIC_PATH, "tiles")), name="tiles")
        app.mount("/icons", StaticFiles(directory=os.path.join(STATIC_PATH, "icons")), name="icons")
        
        # -------- health & root --------
        # TODO(taillades): update burning man geojson to 2025
        @app.get("/")
        async def root() -> FileResponse:  # noqa: D401
            return FileResponse(os.path.join(STATIC_PATH, "map.html"))

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
                left_cmd, right_cmd = self.differential_drive.calculate_wheelchair_states(cmd.speed, cmd.direction)
                self.left_service.control(left_cmd.speed, left_cmd.direction)
                self.right_service.control(right_cmd.speed, right_cmd.direction)
                return {
                    "message": "Couch command received",
                    "speed": cmd.speed,
                    "left_direction": left_cmd.direction,
                    "right_direction": right_cmd.direction,
                    "left_speed": left_cmd.speed,
                    "right_speed": right_cmd.speed,
                    "left_timestamp": left_cmd.timestamp,
                    "right_timestamp": right_cmd.timestamp,
                }
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        # -------- Position --------
        @app.get("/position")
        async def position() -> models.Geopoint | None:  # noqa: D401
            return self.geoposition
        
        @app.get("/theta")
        async def theta() -> float:  # noqa: D401
            """The angle betwen the north-south axis and the wheelchair's direction in radians."""
            return self.theta
        
        @app.post("/target_position")
        async def set_target_position(target: models.Geopoint) -> Dict[str, Any]:  # noqa: D401
            self.target_geopoint = target
            return {"message": "Target position received"}
        
        @app.get("/target_position")
        async def get_target_position() -> models.Geopoint | None:  # noqa: D401
            return self.target_geopoint
        
        @app.delete("/target_position")
        async def clear_target_position() -> Dict[str, str]:  # noqa: D401
            """Clear the current target.

            Sets :pyattr:`self.target_geopoint` to ``None`` so that
            subsequent calls to :http:get:`/target_position` return *null*.
            """
            self.target_geopoint = None
            return {"message": "Target position cleared"}
        
        # -------- Dashboard (static HTML) --------
        @app.get("/dashboard", summary="Live controller dashboard")
        async def dashboard() -> FileResponse:  # noqa: D401
            """Return the HTML dashboard for live telemetry."""
            file_path = Path(__file__).resolve().parent / "static/monitor.html"
            return FileResponse(file_path)
        
        @app.get("/fuel_gauge")
        async def fuel_gauge() -> Dict[str, Any]:  # noqa: D401
            return {
                'left': self.left_service.get_spm_general_information()['fuel_gauge'],
                'right': self.right_service.get_spm_general_information()['fuel_gauge'],
            }
        
        @app.get("/ground_speed")
        async def ground_speed() -> Dict[str, Any]:  # noqa: D401
            return {
                'left': self.left_service.get_spm_general_information()['ground_speed'],
                'right': self.right_service.get_spm_general_information()['ground_speed'],
            }

    # ----------------------------- public API -----------------------------

    def run(self, *, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
        """Run the server with Uvicorn."""
        config = uvicorn.Config(self.app, host=host, port=port, reload=reload, timeout_graceful_shutdown=30)
        server = uvicorn.Server(config)
        server.run()


def run_server(
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    left_serial_port: str,
    right_serial_port: str,
    deadzone: float,
    play_intro: bool,
    reload: bool = False,
) -> None:
    """Convenience wrapper that instantiates :class:`ControllerServer` and calls :py:meth:`ControllerServer.run`."""
    server = ControllerServer(
        left_serial_port=left_serial_port,
        right_serial_port=right_serial_port,
        deadzone=deadzone,
        play_intro=play_intro,
    )
    server.run(host=host, port=port, reload=reload) 