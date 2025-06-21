"""FastAPI server to control the couch using the shark library."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from couch.libs import shark


class WheelchairCommand(BaseModel):
    """Request model for wheelchair commands."""
    speed: float
    direction: float


class WheelchairService:
    """Service class for wheelchair operations."""
    
    def __init__(self, serial_port: str) -> None:
        """
        Initialize the wheelchair service.
        
        :param serial_port: Serial port for the wheelchair controller
        """
        self.serial_port = serial_port
        self.controller = shark.WheelchairController(port=self.serial_port)
        self.controller.start()
    
    def control(self, speed: float, direction: float) -> None:
        """
        Control the wheelchair.
        
        :param speed: Speed value
        :param direction: Direction value
        """
        if not self.controller:
            raise RuntimeError("Wheelchair controller not available")
        self.controller.control(speed, direction)
    
    def get_status(self) -> dict:
        """
        Get current wheelchair status.
        
        :return: Current speed and direction
        """
        if not self.controller:
            raise RuntimeError("Wheelchair controller not available")
        return self.controller.get_status()


class WheelchairServer:
    """Main server class for the wheelchair API."""
    
    def __init__(self, serial_port: str) -> None:
        """
        Initialize the wheelchair server.
        
        :param serial_port: Serial port for the wheelchair controller
        """
        self.service = WheelchairService(serial_port)
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(title="Wheelchair Controller API")
        
        @app.post("/control")
        async def control_wheelchair(command: WheelchairCommand) -> dict:
            """
            Control the wheelchair with speed and direction.
            
            :param command: Wheelchair command with speed and direction
            :return: Confirmation message
            """
            try:
                self.service.control(command.speed, command.direction)
                
                return {
                    "message": "Wheelchair command received",
                    "speed": command.speed,
                    "direction": command.direction
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to control wheelchair: {e}")
        
        @app.get("/status")
        async def get_status() -> dict:
            """
            Get current wheelchair status.
            
            :return: Current speed and direction
            """
            try:
                return self.service.get_status()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")
        
        @app.get("/health")
        async def health() -> dict:
            """
            Check the health of the wheelchair server.
            
            :return: Health status
            """
            return {"status": "healthy"}

        return app


def run_server(serial_port: str, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """
    Run the FastAPI server using uvicorn.
    
    :param serial_port: Serial port for the wheelchair controller
    :param host: Host to bind the server to
    :param port: Port to bind the server to
    :param reload: Whether to enable auto-reload on code changes
    """
    server = WheelchairServer(serial_port)
    
    uvicorn.run(
        server.app,
        host=host,
        port=port,
        reload=reload,
    )




