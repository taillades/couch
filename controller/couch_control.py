import serial
import time

max_speed_const = 255
serial_baud = 38400


def build_runtime_packet(speed_val: int, direction_val: int) -> bytes:
    """
    Build the 10-byte 'type 00 SR General Information' packet.
    
    :param speed_val: 10-bit speed value (0-1023) already mapped
    :param direction_val: 10-bit direction value (0-1023) already mapped
    :return: 10-byte packet as bytes
    """
    data = bytearray(10)
    # General information packet type: 1th bit CLEAR, then length 6 bytes (0b110), then packet type 0 (0b000) -> 0x60
    data[0] = 0x60

    # MSB 7 bits of 10-bit speed_val, direction_val, and max_speed_const
    # Get the 7 MSB of speed_val (out of 10), and SET the 8th bit to 1
    data[1] = 0x80 | ((speed_val >> 3) & 0x7F)
    # Get the 7 MSB of direction_val (out of 10), and SET the 8th bit to 1
    data[2] = 0x80 | ((direction_val >> 3) & 0x7F)
    # Get the 7 MSB of max_speed_const (out of 8), and SET the 8th bit to 1
    data[3] = 0x80 | ((max_speed_const >> 1) & 0x7F)

    # LSB packing
    data[4] = (
        0x80  # Set the 8th bit to 1
        | ((max_speed_const & 0x01) << 6)  # Get the 1 LSB of max_speed_const (out of 8) and place it to the 7th bit
        | ((speed_val & 0x07) << 3)  # Get the 3 LSB of speed_val (out of 10) and place it to the 4th, 5th, and 6th bits
        | (direction_val & 0x07)  # Get the 3 LSB of direction_val (out of 10) and place it to the 1st, 2nd, and 3rd bits
    )

    data[5] = 128  # MSB is SET, then horn off, lock off, no errors
    data[6] = 132  # MSB is SET, then deactivate hazard, indicators, calibration and power OFF, but activate potential SPM HPP messages
    data[7] = 128  # MSB is SET, then no fault, no headlights, and setting drive mode

    chksum = (255 - (sum(data[0:8]) & 0x7F)) & 0xFF
    data[8] = chksum

    data[9] = 15  # This is the transmit finish packet! Technically a separate packet
    return bytes(data)


def map_value(low_in: float, high_in: float, low_out: float, high_out: float, value: float) -> int:
    """
    Map a value from one range to another.
    
    :param low_in: Lower bound of input range
    :param high_in: Upper bound of input range
    :param low_out: Lower bound of output range
    :param high_out: Upper bound of output range
    :param value: Value to map
    :return: Mapped integer value
    """
    return int(low_out + (high_out - low_out) * (value - low_in) / (high_in - low_in))


if __name__ == "__main__":
    ser = serial.Serial(
        port="/dev/tty.usbserial-BG013J1H",  # change to /dev/serial0 or USB adapter
        baudrate=serial_baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        timeout=0.2
    )
    print("Started serial communication")
    time.sleep(0.3)
    speed = 0.0
    direction = 1.0  # left is negative, right is positive
    while True:
        speed_byte = map_value(-1.0, 1.0, 0, 1023, speed)
        direction_byte = map_value(-1.0, 1.0, 0, 1023, direction)
        print(f"Speed: {speed_byte}, Direction: {direction_byte}")

        ser.write(build_runtime_packet(speed_val=speed_byte, direction_val=direction_byte))
        ser.flush()
        time.sleep(0.016)  # Technically needs to be 17.4ms but let's be safe with 16ms
