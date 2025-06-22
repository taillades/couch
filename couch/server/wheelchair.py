"""FastAPI server to control the couch using the shark library."""

from fastapi import FastAPI, HTTPException
import uvicorn

from couch.libs import command, shark

class WheelchairService:
    """Service class for wheelchair operations. Connects to the wheelchair controller and sends commands to it."""
    
    def __init__(self, serial_port: str, max_idle_time: float) -> None:
        """
        Initialize the wheelchair service.
        
        :param serial_port: Serial port for the wheelchair controller
        :param max_idle_time: Maximum idle time in seconds before the controller resets the state to idle.
        """
        self.serial_port = serial_port
        self.controller = shark.WheelchairController(port=self.serial_port, max_idle_time=max_idle_time)
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
    """Main server class for the wheelchair API. Exposes a REST API to control the wheelchair."""
    
    def __init__(self, serial_port: str, max_idle_time: float) -> None:
        """
        Initialize the wheelchair server.
        
        :param serial_port: Serial port for the wheelchair controller
        """
        self.service = WheelchairService(serial_port, max_idle_time)
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(title="Wheelchair Controller API")
        
        @app.post("/control")
        async def control_wheelchair(command: command.WheelchairCommand) -> dict:
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


def run_server(serial_port: str, max_idle_time: float | None = None, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """
    Run the FastAPI server using uvicorn.
    
    :param serial_port: Serial port for the wheelchair controller
    :param max_idle_time: Maximum idle time in seconds before the controller resets the state to idle.
    :param host: Host to bind the server to
    :param port: Port to bind the server to
    :param reload: Whether to enable auto-reload on code changes
    """
    server = WheelchairServer(serial_port, max_idle_time or shark.DEFAULT_MAX_IDLE_TIME)
    
    uvicorn.run(
        server.app,
        host=host,
        port=port,
        reload=reload,
    )




