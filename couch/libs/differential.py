"""Differential drive library."""

from couch.libs import state

class DifferentialDrive:
    """Differential drive library."""

    def __init__(self, distance_between_wheelchairs: float, max_speed: float) -> None:
        self.distance_between_wheelchairs = distance_between_wheelchairs
        self.max_speed = max_speed

    def calculate_wheelchair_states(self, speed: float, direction: float) -> tuple[state.WheelchairState, state.WheelchairState]:
        """Calculate the speeds for the left and right wheels."""
        # TODO (taillades): make sure that the speed, direction and distance between wheelchairs are in the same unit system
        right_wheel_speed = speed + direction * self.distance_between_wheelchairs / 2
        left_wheel_speed = speed - direction * self.distance_between_wheelchairs / 2
        normalization_factor = max(right_wheel_speed, left_wheel_speed, self.max_speed) / self.max_speed
        right_wheel_speed /= normalization_factor
        left_wheel_speed /= normalization_factor
        return (
            state.WheelchairState(speed=right_wheel_speed, direction=direction),
            state.WheelchairState(speed=left_wheel_speed, direction=direction)
        )