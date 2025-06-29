import math
import os
import requests
import asyncio
import aiohttp

# Constants
CENTER_LAT = 40.8328
CENTER_LON = -119.1600
ZOOM_LEVEL_VS_RADIUS_KM = {
    3: 111 * 360,
    4: 111 * 360,
    5: 111 * 360,
    6: 111 * 360,
    7: 1200,
    8: 320,
    9: 160,
    10: 80,
    11: 40,
    12: 40,
    13: 20,
    14: 20,
    15: 5,
    16: 5,
    17: 5,
    18: 5,
    19: 5,
}

TILES_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "tiles")

TILE_SERVER_URL = "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoidGFpbGxhZGVzIiwiYSI6ImNtY2g5dWE1eDB1MHUyanEyN3o4ZDZzangifQ.wAcuJo6gcuSyDkAFEBprig"


# Convert lat/lon to tile
def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_tile = int((lon + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile

# Approximate lat/lon bounds in degrees (1 deg ~ 111 km)
def get_bounds(lat, lon, radius_km):
    delta_deg = radius_km / 111.0
    return (
        lat - delta_deg, lat + delta_deg,   # min_lat, max_lat
        lon - delta_deg, lon + delta_deg    # min_lon, max_lon
    )

# Download a single tile
def download_tile(z, x, y, folder=TILES_PATH):
    url = TILE_SERVER_URL.format(z=z, x=x, y=y)
    path = os.path.join(folder, str(z), str(x))
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{y}.png")

    if not os.path.exists(file_path):
        response = requests.get(url, timeout=100)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download tile z={z} x={x} y={y}: {response.status_code}")


async def async_download_tile(z: int, x: int, y: int, folder: str = TILES_PATH) -> None:
    """
    Download a single tile asynchronously.

    :param z: Zoom level
    :param x: Tile x coordinate
    :param y: Tile y coordinate
    :param folder: Output folder
    """
    url = TILE_SERVER_URL.format(z=z, x=x, y=y)
    path = os.path.join(folder, str(z), str(x))
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{y}.png")

    if not os.path.exists(file_path):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=100) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
                        print(f"Downloaded tile z={z} x={x} y={y}")
                    else:
                        print(f"Failed to download tile z={z} x={x} y={y}: {response.status}")
            except Exception as e:
                print(f"Failed tile z={z} x={x} y={y}: {e}")

async def download_tiles(lat: float, lon: float, radius_km: float, zoom_levels: list) -> None:
    """
    Download all tiles asynchronously for the given parameters.

    :param lat: Center latitude
    :param lon: Center longitude
    :param radius_km: Radius in kilometers
    :param zoom_levels: List of zoom levels
    """
    min_lat, max_lat, min_lon, max_lon = get_bounds(lat, lon, radius_km)

    for z in zoom_levels:
        x_start, y_start = latlon_to_tile(max_lat, min_lon, z)
        x_end, y_end = latlon_to_tile(min_lat, max_lon, z)

        print(f"Zoom {z}: downloading tiles x={x_start}-{x_end}, y={y_start}-{y_end}")

        tasks = []
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                if not os.path.exists(os.path.join(TILES_PATH, str(z), str(x), f"{y}.png")):
                    tasks.append(async_download_tile(z, x, y))
        await asyncio.gather(*tasks)
    

# Run it
if __name__ == "__main__":
    for zoom_level, radius_km in ZOOM_LEVEL_VS_RADIUS_KM.items():
        asyncio.run(download_tiles(CENTER_LAT, CENTER_LON, radius_km, [zoom_level]))
