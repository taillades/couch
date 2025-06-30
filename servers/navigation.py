"""Navigation server. Should be run on a separate machine from the controller."""

from __future__ import annotations

import asyncio
import datetime
import math
from contextlib import asynccontextmanager
import contextlib
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from libs import models


STATIC_PATH = Path(__file__).resolve().parent.parent / "static"


class NavigationServer:
    """High-level navigation server commanding the low-level controller via HTTP."""

    def __init__(
        self,
        *,
        controller_host: str,
        controller_port: int,
        thermo_serial_port: str,
        gps_serial_port: str,
    ) -> None:
        """Instantiate the navigation server.

        :param controller_host: Hostname or IP of the controller server
        :param controller_port: Port of the controller server
        :param thermo_serial_port: Serial port for the temperature sensor
        :param gps_serial_port: Serial port for the GPS
        """
        self.controller_url = f"http://{controller_host}:{controller_port}"
        self._controller_healthy: bool = False
        # Check the controller health once during startup
        try:
            asyncio.run(self._check_controller_health())
        except RuntimeError:
            # If an event loop is already running, schedule the coroutine instead.
            loop = asyncio.get_running_loop()
            loop.create_task(self._check_controller_health())

        # State
        self.target_geopoint: models.Geopoint | None = None
        self.theta: float = math.radians(45)

        self._client_controller: httpx.AsyncClient | None = None
        self._task_loop: asyncio.Task[None] | None = None

        self.app = FastAPI(title="Couch Navigation Server", version="1.0.0", lifespan=self._lifespan)
        self._setup_routes()

    # ------------------------------------------------------------------
    # Lifespan
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI) -> AsyncGenerator[None, Any]:
        """Create the HTTP client and background control-loop."""
        async with httpx.AsyncClient() as client:
            self._client_controller = client
            self._task_loop = asyncio.create_task(self._control_loop())
            try:
                yield
            finally:
                if self._task_loop:
                    self._task_loop.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._task_loop
                self._client_controller = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _check_controller_health(self) -> bool:
        """
        Check whether the controller back-end is alive.

        The method queries the ``/health`` endpoint of the controller and updates
        :pyattr:`_controller_healthy` accordingly.

        Returns
        -------
        True if the controller responds with a JSON payload ``{"status": "healthy"}``, False otherwise.
        """
        if self._client_controller is None:
            # Create a temporary client for the one-off probe when the shared client
            # has not been instantiated yet (e.g. during object construction).
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{self.controller_url}/health", timeout=2.0)
                    healthy = resp.status_code == 200 and resp.json().get("status") == "healthy"
                    self._controller_healthy = healthy
                    return healthy
                except Exception:
                    self._controller_healthy = False
                    return False

        try:
            resp = await self._client_controller.get(f"{self.controller_url}/health", timeout=2.0)
            healthy = resp.status_code == 200 and resp.json().get("status") == "healthy"
            self._controller_healthy = healthy
            return healthy
        except Exception:
            self._controller_healthy = False
            return False

    def compute_autonomous_command(self) -> tuple[float, float]:
        """Return speed and direction to reach :pyattr:`target_geopoint`."""
        if self.target_geopoint is None or self.geoposition is None:
            return 0.0, 0.0
        lat1, lon1 = self.geoposition.lat, self.geoposition.lon
        lat2, lon2 = self.target_geopoint.lat, self.target_geopoint.lon
        R = 6_371_000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        if distance < 3.0:
            return 0.0, 0.0
        y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
        bearing = math.atan2(y, x)
        direction = bearing - self.theta
        while direction > math.pi:
            direction -= 2 * math.pi
        while direction < -math.pi:
            direction += 2 * math.pi
        return 1.0, max(-1.0, min(1.0, direction))

    def _simulate_movement(self, speed: float, direction: float) -> None:
        """Update :pyattr:`geoposition` and :pyattr:`theta` for testing."""
        direction = max(-0.2, min(0.2, direction))
        mph_to_degree_for_20ms = 69 * 50 * 3600
        speed /= mph_to_degree_for_20ms
        speed *= 100
        if self.geoposition is None:
            return
        self.geoposition = models.Geopoint(
            lat=self.geoposition.lat + speed * math.cos(self.theta),
            lon=self.geoposition.lon + speed * math.sin(self.theta),
        )
        self.theta = max(-math.pi / 2, min(math.pi / 2, self.theta + direction / (1 + speed)))

    async def _post_controller_command(self, speed: float, direction: float) -> None:
        """Send a command to the controller."""
        if self._client_controller is None:
            return
        payload: Dict[str, Any] = {
            "speed": speed,
            "direction": direction,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        await self._client_controller.post(f"{self.controller_url}/controller/control", json=payload, timeout=1.0)

    async def _control_loop(self) -> None:
        """Background loop computing and sending commands."""
        while True:
            try:
                start = asyncio.get_running_loop().time()
                speed, direction = self.compute_autonomous_command()
                self._simulate_movement(speed, direction)
                if speed != 0.0 or direction != 0.0:
                    await self._post_controller_command(speed, direction)
                elapsed = asyncio.get_running_loop().time() - start
                await asyncio.sleep(max(0.0, 0.02 - elapsed)) # safety margin but it should run all the time
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"Navigation control-loop error: {exc}")
                await asyncio.sleep(0.02) # safety margin but it should run all the time

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    def _setup_routes(self) -> None:
        app = self.app

        # Static assets
        app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")
        app.mount("/js", StaticFiles(directory=STATIC_PATH / "js"), name="js")
        app.mount("/burning_man_2023_geojson", StaticFiles(directory=STATIC_PATH / "burning_man_2023_geojson"), name="geojson")
        app.mount("/tiles", StaticFiles(directory=STATIC_PATH / "tiles"), name="tiles")
        app.mount("/icons", StaticFiles(directory=STATIC_PATH / "icons"), name="icons")

        @app.get("/")
        async def root() -> FileResponse:  # noqa: D401
            return FileResponse(STATIC_PATH / "map.html")

        @app.get("/health")
        async def health() -> Dict[str, str]:  # noqa: D401
            return {"status": "healthy"}

        @app.get("/position")
        async def position() -> models.Geopoint | None:  # noqa: D401
            return self.geoposition

        @app.get("/theta")
        async def theta() -> float:  # noqa: D401
            return self.theta

        @app.post("/target_position")
        async def set_target_position(target: models.Geopoint) -> Dict[str, str]:  # noqa: D401
            self.target_geopoint = target
            return {"message": "Target position received"}

        @app.get("/target_position")
        async def get_target_position() -> models.Geopoint | None:  # noqa: D401
            return self.target_geopoint

        @app.delete("/target_position")
        async def clear_target_position() -> Dict[str, str]:  # noqa: D401
            self.target_geopoint = None
            return {"message": "Target position cleared"}

        @app.get("/dashboard", summary="Live navigation dashboard")
        async def dashboard() -> FileResponse:  # noqa: D401
            return FileResponse(STATIC_PATH / "monitor.html")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, *, host: str, port: int) -> None:
        """Serve the application with Uvicorn."""
        config = uvicorn.Config(self.app, host=host, port=port, timeout_graceful_shutdown=30)
        uvicorn.Server(config).run()


def run_server(
    *,
    host: str,
    port: int,
    controller_host: str,
    controller_port: int,
    thermo_serial_port: str,
    gps_serial_port: str,
) -> None:
    """Convenience wrapper for :class:`NavigationServer`."""
    server = NavigationServer(
        controller_host=controller_host,
        controller_port=controller_port,
        thermo_serial_port=thermo_serial_port,
        gps_serial_port=gps_serial_port,
    )
    server.run(host=host, port=port)