"""State classes."""

from dataclasses import dataclass


@dataclass
class WheelchairState:
    """Current state of the wheelchair."""
    speed: float = 0.0
    direction: float = 0.0
