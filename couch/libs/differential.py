"""Differential drive library."""

from couch.libs import state

class DifferentialDrive:
    """Differential drive library."""

    def __init__(self, distance_between_wheelchairs: float) -> None:
        self.distance_between_wheelchairs = distance_between_wheelchairs

    def calculate_wheelchair_states(self, speed: float, direction: float) -> tuple[state.WheelchairState, state.WheelchairState]:
        """Calculate the speeds for the left and right wheels."""
        right_wheel_speed = speed + direction * self.distance_between_wheelchairs / 2
        left_wheel_speed = speed - direction * self.distance_between_wheelchairs / 2
        return (
            state.WheelchairState(speed=right_wheel_speed, direction=direction),
            state.WheelchairState(speed=left_wheel_speed, direction=direction)
        )