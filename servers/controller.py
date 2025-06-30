from __future__ import annotations

from contextlib import asynccontextmanager, suppress
import datetime
from typing import Any, AsyncGenerator, Dict
import os
import asyncio

import uvicorn
from fastapi import FastAPI, HTTPException

from libs import differential, models, shark, xbox

class ControllerServer:
    """Unified server that embeds joystick reading, differential control and direct wheelchair commands."""

    def __init__(
        self,
        *,
        left_serial_port: str,
        right_serial_port: str,
        deadzone: float,
    ) -> None:
        """Build the unified server.

        :param left_serial_port: Serial port for the left wheelchair controller
        :param right_serial_port: Serial port for the right wheelchair controller
        :param deadzone: Ignore absolute joystick values below this threshold
        """
        self.left_service = shark.WheelchairController(port=left_serial_port)
        self.right_service = shark.WheelchairController(port=right_serial_port)
        self.remote = xbox.XboxRemote(
            callbacks={
                'button_down': lambda _: xbox.play_music_callback('fuck_your_burn'),
                'button_a': lambda _: self._set_allow_navigation(True),
                'button_b': lambda _: self._set_allow_navigation(False),
            },
            deadzone=deadzone,
        )
        
        self.differential_drive = differential.DifferentialDrive()
        self.navigation_command = models.WheelchairCommand(speed=0.0, direction=0.0, timestamp=datetime.datetime.now())
        self.allow_navigation = True
        
        self.deadzone = deadzone
        
        self.app = FastAPI(title="Couch Unified Server", version="1.0.0", lifespan=self._lifespan)
        self._setup_routes()

        self._task_loop: asyncio.Task | None = None

    # ----------------------------- lifespan -----------------------------

    def _set_allow_navigation(self, allow: bool) -> None:
        """Set the allow navigation flag."""
        self.allow_navigation = allow
        if not allow:
            # Reset the navigation so your dont' have a ghost command sitting around
            self.navigation_command = models.WheelchairCommand(speed=0.0, direction=0.0, timestamp=datetime.datetime.now())

    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI) -> AsyncGenerator[None, Any]:
        """
        Manage application lifespan.

        On startup, start the Xbox remote listener and both wheelchair controllers.
        On shutdown, stop all hardware services to free the serial ports.
        """
        self.remote.start()
        self.left_service.start()
        self.right_service.start()
        self._task_loop = asyncio.create_task(self._control_loop())
        try:
            yield
        finally:
            if self._task_loop:
                self._task_loop.cancel()
                with suppress(asyncio.CancelledError):
                    await self._task_loop
            self.remote.stop()
            self.left_service.stop()
            self.right_service.stop()

    async def _control_loop(self) -> None:
        """Background loop reading joystick and driving the wheelchairs."""
        while True:
            try:
                start = asyncio.get_running_loop().time()
                speed, direction = self._get_speed_direction_from_controller()
                if speed == 0.0 and direction == 0.0 and self.allow_navigation:
                    speed = self.navigation_command.speed
                    direction = self.navigation_command.direction
                left_cmd, right_cmd = self.differential_drive.calculate_wheelchair_states(speed, direction)
                self.left_service.control(left_cmd.speed, left_cmd.direction)
                self.right_service.control(right_cmd.speed, right_cmd.direction)
                elapsed = asyncio.get_running_loop().time() - start
                await asyncio.sleep(max(0.0, 0.02 - elapsed))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"Controller control-loop error: {exc}")
                await asyncio.sleep(0.02)

    # ----------------------------- internal helpers -----------------------------

    def _apply_deadzone(self, value: float) -> float:
        """Return 0 if *value* lies inside the deadzone."""
        return 0.0 if abs(value) < self.deadzone else value
    
    def _get_speed_direction_from_controller(self) -> tuple[float, float]:
        """Get the speed and direction from the joystick."""
        speed, direction = self.remote.get_joystick_speed_direction()
        speed = self._apply_deadzone(speed)
        direction = self._apply_deadzone(direction)
        return speed, direction

    # ----------------------------- routes -----------------------------

    def _setup_routes(self) -> None:
        app = self.app

        @app.get("/")
        async def root() -> Dict[str, str]:  # noqa: D401
            return {"message": "Couch controller server is running"}

        @app.get("/health")
        async def health() -> Dict[str, str]:  # noqa: D401
            return {"status": "healthy"}
        
        @app.get("/navigation/allow")
        async def get_allow_navigation() -> Dict[str, bool]:  # noqa: D401
            return {"allow": self.allow_navigation}
        
        @app.post("/navigation/command")
        async def set_navigation_command(cmd: models.WheelchairCommand) -> Dict[str, Any]:  # noqa: D401
            self.navigation_command = models.WheelchairCommand(
                speed=cmd.speed,
                direction=cmd.direction,
                timestamp=datetime.datetime.now(),
            )
            return {"message": "Navigation command received"}

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
        
        @app.get("/joystick", response_model=models.JoystickData)
        async def get_joystick() -> models.JoystickData:  # noqa: D401
            """Get the current joystick state."""
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

        @app.post("/wheelchair/left/control")
        async def left_control(cmd: models.WheelchairCommand) -> Dict[str, Any]:  # noqa: D401
            """Control the left wheelchair."""
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
            """Control the right wheelchair."""
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
            """Get the status of the left wheelchair."""
            return self.left_service.get_status()

        @app.get("/wheelchair/right/status")
        async def right_status() -> Dict[str, Any]:  # noqa: D401
            """Get the status of the right wheelchair."""
            return self.right_service.get_status()

    def run(self, *, host: str, port: int) -> None:
        """Run the server with Uvicorn."""
        config = uvicorn.Config(self.app, host=host, port=port, timeout_graceful_shutdown=30)
        server = uvicorn.Server(config)
        server.run()


def run_server(
    *,
    host: str,
    port: int,
    left_serial_port: str,
    right_serial_port: str,
    deadzone: float,
) -> None:
    """Convenience wrapper that instantiates :class:`ControllerServer` and calls :py:meth:`ControllerServer.run`."""
    server = ControllerServer(
        left_serial_port=left_serial_port,
        right_serial_port=right_serial_port,
        deadzone=deadzone,
    )
    server.run(host=host, port=port) 