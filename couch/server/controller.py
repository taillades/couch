"""Controller for the wheelchair."""

from typing import Final

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException

from couch.libs import command, differential

DEFAULT_DISTANCE_BETWEEN_WHEELCHAIRS: Final[float] = 1.01  # meters


class Controller:
    """Controller for differential drive wheelchair system."""

    def __init__(
        self,
        *,
        left_wheelchair_url: str,
        right_wheelchair_url: str,
        distance_between_wheelchairs: float,
    ) -> None:
        """
        Initialize the differential wheelchair controller.

        :param left_wheelchair_url: URL of the left wheelchair
        :param right_wheelchair_url: URL of the right wheelchair
        :param distance_between_wheelchairs: Distance between left and right wheelchairs
        """
        self.differential_drive = differential.DifferentialDrive(
            distance_between_wheelchairs
        )
        self.left_wheelchair_url = left_wheelchair_url
        self.right_wheelchair_url = right_wheelchair_url

    async def control(self, speed: float, direction: float) -> None:
        """
        Control both wheelchairs using differential drive.

        :param speed: Speed value between -1.0 and 1.0
        :param direction: Direction value between -1.0 and 1.0
        """
        left_state, right_state = self.differential_drive.calculate_wheelchair_states(
            speed, direction
        )
        async with httpx.AsyncClient() as client:
            try:
                for url, state in [
                    (self.left_wheelchair_url, left_state),
                    (self.right_wheelchair_url, right_state),
                ]:
                    resp = await client.post(
                        f"{url}/control",
                        json={"speed": state.speed, "direction": state.direction},
                        timeout=5.0,
                    )
                    resp.raise_for_status()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to communicate with wheelchair servers: {e}",
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Wheelchair server error: {e}",
                )

    async def get_status(self) -> dict:
        """
        Get current status from both wheelchairs.

        :return: Combined status from both wheelchairs
        """
        async with httpx.AsyncClient() as client:
            try:
                statuses = {}
                for name, url in [
                    ("left_wheelchair", self.left_wheelchair_url),
                    ("right_wheelchair", self.right_wheelchair_url),
                ]:
                    resp = await client.get(f"{url}/status", timeout=5.0)
                    resp.raise_for_status()
                    status = resp.json()
                    statuses[name] = status
                return statuses

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get status from wheelchair servers: {e}",
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Wheelchair server error: {e}",
                )


class ControllerServer:
    """Main server class for the differential wheelchair API."""

    def __init__(
        self,
        left_wheelchair_url: str,
        right_wheelchair_url: str,
        distance_between_wheelchairs: float,
    ) -> None:
        """
        Initialize the differential wheelchair server.

        :param left_wheelchair_url: URL of the left wheelchair
        :param right_wheelchair_url: URL of the right wheelchair
        :param distance_between_wheelchairs: Distance between left and right wheelchairs
        """
        self.controller = Controller(
            left_wheelchair_url=left_wheelchair_url,
            right_wheelchair_url=right_wheelchair_url,
            distance_between_wheelchairs=distance_between_wheelchairs,
        )
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(title="Differential Wheelchair Controller API")

        @app.post("/control")
        async def control_wheelchairs(command: command.WheelchairCommand) -> dict:
            """
            Control both wheelchairs with speed and direction using differential drive.

            :param command: Wheelchair command with speed and direction
            :return: Confirmation message
            """
            try:
                await self.controller.control(command.speed, command.direction)

                return {
                    "message": "Differential wheelchair command received",
                    "speed": command.speed,
                    "direction": command.direction,
                    "left_wheelchair_url": self.controller.left_wheelchair_url,
                    "right_wheelchair_url": self.controller.right_wheelchair_url,
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to control wheelchairs: {e}"
                )

        @app.get("/status")
        async def get_status() -> dict:
            """
            Get current status from both wheelchairs.

            :return: Combined status from both wheelchairs
            """
            try:
                return await self.controller.get_status()
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to get status: {e}"
                )

        @app.get("/health")
        async def health() -> dict:
            """
            Check the health of the differential wheelchair server.

            :return: Health status
            """
            return {"status": "healthy"}

        return app


def run_server(
    left_wheelchair_url: str,
    right_wheelchair_url: str,
    distance_between_wheelchairs: float | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """
    Run the FastAPI server using uvicorn.

    :param left_wheelchair_url: URL of the left wheelchair
    :param right_wheelchair_url: URL of the right wheelchair
    :param distance_between_wheelchairs: Distance between left and right wheelchairs
    :param host: Host to bind the server to
    :param port: Port to bind the server to
    :param reload: Whether to enable auto-reload on code changes
    """
    server = ControllerServer(
        left_wheelchair_url=left_wheelchair_url,
        right_wheelchair_url=right_wheelchair_url,
        distance_between_wheelchairs=distance_between_wheelchairs or DEFAULT_DISTANCE_BETWEEN_WHEELCHAIRS,
    )

    uvicorn.run(
        server.app,
        host=host,
        port=port,
        reload=reload,
    )
