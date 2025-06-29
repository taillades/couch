"""Differential drive library."""

import datetime
from libs import models

# This has been fine tuned for our couch
DEFAULT_DISTANCE_BETWEEN_WHEELCHAIRS = 10
DEFAULT_MAX_SPEED = 1.0
DEFAULT_MAX_DIRECTION = 0.2

def _zero_safe_division(a: float, b: float) -> float:
    if b == 0:
        return 2**100
    return a / b

def _sign(a: float) -> float:
    if a == 0:
        return 0
    return 1 if a > 0 else -1

class DifferentialDrive:
    """Differential drive library."""

    def __init__(self, 
                 distance_between_wheelchairs: float = DEFAULT_DISTANCE_BETWEEN_WHEELCHAIRS, 
                 max_speed: float = DEFAULT_MAX_SPEED, 
                 max_direction: float = DEFAULT_MAX_DIRECTION) -> None:
        """
        :param distance_between_wheelchairs: Center-to-center distance between wheelchairs (in meters)
        :param max_speed: Maximum speed for the wheelchairs (from shark.MAX_SPEED env var if not provided)
        :param max_direction: Maximum direction for the wheelchairs (from shark.MAX_DIRECTION env var if not provided)
        """
        self.distance_between_wheelchairs = distance_between_wheelchairs
        self.max_speed = max_speed
        self.max_direction = max_direction

    def calculate_wheelchair_states(self, speed: float, direction: float) -> tuple[models.WheelchairCommand, models.WheelchairCommand]:
        """Calculate the speeds for the left and right wheels."""
        # TODO (taillades): make sure that the speed, direction and distance between wheelchairs are in the same unit system
        right_speed = speed + direction / 2
        left_speed = speed - direction / 2

        max_speed = max(abs(right_speed), abs(left_speed))
        if max_speed > self.max_speed:
            right_speed = right_speed * self.max_speed / max_speed
            left_speed = left_speed * self.max_speed / max_speed

        ICR_radius = (self.distance_between_wheelchairs / 2) * _zero_safe_division(right_speed + left_speed, right_speed - left_speed)
        
        right_direction = right_speed / (ICR_radius + self.distance_between_wheelchairs / 2 * _sign(direction))
        left_direction = left_speed / (ICR_radius - self.distance_between_wheelchairs / 2 * _sign(direction))
        
        max_direction = max(abs(right_direction), abs(left_direction))
        if max_direction > self.max_direction:
            right_direction = right_direction * self.max_direction / max_direction
            left_direction = left_direction * self.max_direction / max_direction
        
        return (
            models.WheelchairCommand(speed=right_speed, direction=right_direction, timestamp=datetime.datetime.now()),
            models.WheelchairCommand(speed=left_speed, direction=left_direction, timestamp=datetime.datetime.now() )
        )