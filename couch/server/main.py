"""Main server that reads joystick data and controls wheelchairs."""

import asyncio
from typing import Optional

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
import uvicorn

from couch.server.joystick import JoystickData

DEFAULT_UPDATE_RATE = 20.0
DEFAULT_DEADZONE = 0.1

class MainServer:
    """Main server that coordinates joystick input and wheelchair control."""
    
    def __init__(
        self,
        joystick_server_url: str,
        controller_server_url: str,
        update_rate: float = DEFAULT_UPDATE_RATE,
        deadzone: float = DEFAULT_DEADZONE
    ) -> None:
        """
        Initialize the main server.
        
        Args:
            joystick_server_url: URL of the joystick server
            controller_server_url: URL of the controller server
            update_rate: Update rate in Hz for the control loop
            deadzone: Minimum joystick value to register as input
        """
        self.joystick_server_url = joystick_server_url.rstrip('/')
        self.controller_server_url = controller_server_url.rstrip('/')
        self.update_rate = update_rate
        self.deadzone = deadzone
        
        self.app = FastAPI(title="Main Control Server", version="1.0.0", lifespan=self._lifespan)
        self._setup_routes()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """
        Lifespan context manager for startup and shutdown events.

        Args:
            app: FastAPI application instance
        """
        # Start the control loop
        self._control_task = asyncio.create_task(self._control_loop())
        print("Main server started")
        
        yield
        
        # Stop the control loop
        if hasattr(self, '_control_task'):
            self._control_task.cancel()
            try:
                await self._control_task
            except asyncio.CancelledError:
                pass
        print("Main server stopped")
        
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root() -> dict:
            """Root endpoint."""
            return {
                "message": "Main Control Server",
                "joystick_server": self.joystick_server_url,
                "controller_server": self.controller_server_url,
                "update_rate": self.update_rate
            }
        
        @self.app.get("/health")
        async def health() -> dict:
            """Health check endpoint."""
            return {"status": "healthy"}
        
        @self.app.get("/status")
        async def get_status() -> dict:
            """Get current status."""
            return {
                "joystick_server": self.joystick_server_url,
                "controller_server": self.controller_server_url,
                "update_rate": self.update_rate,
                "deadzone": self.deadzone
            }
    
    def _apply_deadzone(self, value: float) -> float:
        """
        Apply deadzone to joystick values.
        
        Args:
            value: Input value between -1.0 and 1.0
            
        Returns:
            Value with deadzone applied
        """
        if abs(value) < self.deadzone:
            return 0.0
        return value
    
    async def _read_joystick_data(self) -> Optional[JoystickData]:
        """
        Read joystick data from the joystick server.
        
        Returns:
            Joystick data or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{self.joystick_server_url}/joystick")
                response.raise_for_status()
                data = response.json()
                return JoystickData(**data)
        except Exception as e:
            print(f"Failed to read joystick data: {e}")
            return None
    
    async def _send_control_command(self, speed: float, direction: float) -> bool:
        """
        Send control command to the controller server.
        
        Args:
            speed: Speed value between -1.0 and 1.0
            direction: Direction value between -1.0 and 1.0
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    f"{self.controller_server_url}/control",
                    json={"speed": speed, "direction": direction}
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Failed to send control command: {e}")
            return False
    
    async def _control_loop(self) -> None:
        """Main control loop that reads joystick and sends commands."""
        print("Control loop started")
        while True:
            try:
                # Read joystick data
                joystick_data = await self._read_joystick_data()
                
                if joystick_data:
                    # Apply deadzone
                    speed = self._apply_deadzone(joystick_data.speed)
                    direction = self._apply_deadzone(joystick_data.direction)
                    success = await self._send_control_command(speed, direction)
                    if not success:
                        print(f"Failed to send control command: speed={speed:.3f}, direction={direction:.3f}")
            
                # Wait for next update
                await asyncio.sleep(1.0 / self.update_rate)
                
            except Exception as e:
                print(f"Error in control loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
        
        print("Control loop stopped")
    
    def run(self, host: str = "0.0.0.0", port: int = 8001) -> None:
        """
        Run the main server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        uvicorn.run(self.app, host=host, port=port)


def run_server(
    host: str,
    port: int,
    joystick_server_url: str,
    controller_server_url: str,
    update_rate: float | None = None,
    deadzone: float | None = None,
) -> None:
    """
    Run the main control server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        joystick_server_url: URL of the joystick server
        controller_server_url: URL of the controller server
        update_rate: Update rate in Hz for the control loop
        deadzone: Minimum joystick value to register as input
    """
    server = MainServer(
        joystick_server_url=joystick_server_url,
        controller_server_url=controller_server_url,
        update_rate=update_rate or DEFAULT_UPDATE_RATE,
        deadzone=deadzone or DEFAULT_DEADZONE
    )
    server.run(host=host, port=port)
