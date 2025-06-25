"""Normalization functions."""


def normalize_range(input_min: float, input_max: float, output_min: float, output_max: float, input_value: float) -> int:
    """
    Normalize a value from an input range to an output range using linear interpolation.

    :param input_min: Minimum value of input range
    :param input_max: Maximum value of input range
    :param output_min: Minimum value of output range
    :param output_max: Maximum value of output range
    :param input_value: Value to normalize from input range to output range
    :return: Input value normalized to output range and rounded to nearest integer
    """
    input_percent = (input_value - input_min) / (input_max - input_min)
    output_value = output_min + (output_max - output_min) * input_percent
    return int(output_value)