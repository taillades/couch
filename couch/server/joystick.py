"""Server for providing joystick data via HTTP API."""

from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from couch.libs import xbox


class JoystickData(BaseModel):
    """Joystick data model."""
    speed: float
    direction: float
    x: float
    y: float
    button_a: bool
    button_b: bool


class JoystickServer:
    """Server for providing joystick data via HTTP API."""
    
    def __init__(self) -> None:
        """Initialize the joystick server."""
        self.remote: Optional[xbox.XboxRemote] = None
        self.app = FastAPI(title="Joystick Server", version="1.0.0", lifespan=self._lifespan)
        self._setup_routes()
        
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Lifespan context manager for startup and shutdown events."""
        try:
            self.remote = xbox.XboxRemote()
            self.remote.start()
            print("Joystick controller initialized and started")
        except Exception as e:
            print(f"Failed to initialize joystick controller: {e}")
            
        yield
        
        if self.remote:
            self.remote.stop()
            print("Joystick controller stopped")
        
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root() -> Dict[str, str]:
            """Root endpoint."""
            return {"message": "Joystick Server", "status": "running"}
        
        @self.app.get("/health")
        async def health() -> Dict[str, str]:
            """Health check endpoint."""
            return {"status": "healthy"}
            
        @self.app.get("/joystick", response_model=JoystickData)
        async def get_joystick_data() -> JoystickData:
            """Get current joystick and button data."""
            if not self.remote:
                raise HTTPException(status_code=503, detail="Controller not initialized")

            speed, direction = self.remote.get_joystick_speed_direction()
            x, y = self.remote.get_joystick_xy()
            
            return JoystickData(
                speed=speed,
                direction=direction,
                x=x,
                y=y,
                button_a=self.remote.button_a,
                button_b=self.remote.button_b
            )
            
        @self.app.get("/joystick/speed-direction")
        async def get_speed_direction() -> Dict[str, float]:
            """Get speed and direction only."""
            if not self.remote:
                raise HTTPException(status_code=503, detail="Controller not initialized")
                
            speed, direction = self.remote.get_joystick_speed_direction()
            return {"speed": speed, "direction": direction}
            
        @self.app.get("/joystick/xy")
        async def get_xy() -> Dict[str, float]:
            """Get X and Y joystick values only."""
            if not self.remote:
                raise HTTPException(status_code=503, detail="Controller not initialized")
                
            x, y = self.remote.get_joystick_xy()
            return {"x": x, "y": y}
            
        @self.app.get("/buttons")
        async def get_buttons() -> Dict[str, bool]:
            """Get button states only."""
            if not self.remote:
                raise HTTPException(status_code=503, detail="Controller not initialized")
                
            return {
                "button_a": self.remote.button_a,
                "button_b": self.remote.button_b
            }
            
        @self.app.get("/status")
        async def get_status() -> Dict[str, Any]:
            """Get controller status."""
            if not self.remote:
                return {"connected": False, "error": "Controller not initialized"}
                
            connected = self.remote.is_connected()
            return {
                "connected": connected,
                "running": self.remote._running
            }
            
    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """
        Run the joystick server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        uvicorn.run(self.app, host=host, port=port)

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the joystick server."""
    server = JoystickServer()
    uvicorn.run(server.app, host=host, port=port, reload=reload)

