"""Differential drive library."""

import datetime
from libs import models

class DifferentialDrive:
    """Differential drive library."""

    def __init__(self, distance_between_wheelchairs: float, max_speed: float, max_direction: float) -> None:
        self.distance_between_wheelchairs = distance_between_wheelchairs
        self.max_speed = max_speed
        self.max_direction = max_direction

    def calculate_wheelchair_states(self, speed: float, direction: float) -> tuple[models.WheelchairCommand, models.WheelchairCommand]:
        """Calculate the speeds for the left and right wheels."""
        # TODO (taillades): make sure that the speed, direction and distance between wheelchairs are in the same unit system
        right_wheel_speed = speed + direction * self.distance_between_wheelchairs / 2
        left_wheel_speed = speed - direction * self.distance_between_wheelchairs / 2
        normalization_factor = max(abs(right_wheel_speed), abs(left_wheel_speed), self.max_speed) / self.max_speed
        right_wheel_speed /= normalization_factor
        left_wheel_speed /= normalization_factor
        
        direction_normalization_factor = max(abs(right_wheel_speed), abs(left_wheel_speed), self.max_direction) / self.max_direction
        direction /= direction_normalization_factor
        
        return (
            models.WheelchairCommand(speed=right_wheel_speed, direction=direction, timestamp=datetime.datetime.now()),
            models.WheelchairCommand(speed=left_wheel_speed, direction=direction, timestamp=datetime.datetime.now() )
        )