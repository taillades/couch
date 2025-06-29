"""Command classes."""

import datetime

from pydantic import BaseModel

class JoystickData(BaseModel):
    """Joystick data model."""
    speed: float
    direction: float
    x: float
    y: float
    button_a: bool
    button_b: bool
    button_x: bool
    button_y: bool
    button_up: bool
    button_down: bool
    button_left: bool
    button_right: bool
    button_start: bool

class WheelchairCommand(BaseModel):
    """Request model for wheelchair commands."""
    speed: float = 0.0
    direction: float = 0.0
    timestamp: datetime.datetime
    
class Geopoint(BaseModel):
    """Geopoint model."""
    lat: float
    lon: float
    