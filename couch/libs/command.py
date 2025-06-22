"""Command classes."""

from pydantic import BaseModel


class WheelchairCommand(BaseModel):
    """Request model for wheelchair commands."""
    speed: float
    direction: float
    
class WheelchairStatus(BaseModel):
    """Response model for wheelchair status."""
    speed: float
    direction: float

class CouchCommand(BaseModel):
    """Request model for couch commands."""
    speed: float
    direction: float

class CouchStatus(BaseModel):
    """Response model for couch status."""
    speed: float
    direction: float