"""State classes."""

from dataclasses import dataclass

import datetime


@dataclass
class WheelchairState:
    """Current state of the wheelchair."""
    last_command_timestamp: datetime.datetime
    speed: float = 0.0
    direction: float = 0.0
