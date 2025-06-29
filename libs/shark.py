"""Wheelchair control library for serial communication."""

from typing import Final
import time
import threading

import serial
import datetime

from libs import normalization, models

MAX_SPEED: Final[int] = 255
BAUD_RATE: Final[int] = 38400
START_WAIT_TIME: Final[float] = 0.3
LOOP_WAIT_TIME: Final[float] = 0.016
DEFAULT_MAX_IDLE_TIME: Final[float] = 1.0  # seconds
NOMINAL_MAX_SPEED: Final[float] = 4.5 # mph


def build_runtime_packet(speed: int, direction: int) -> bytes:
    """
    Build the 10-byte 'type 00 SR General Information' packet.
    
    :param speed: 10-bit speed value (0-1023) already mapped
    :param direction: 10-bit direction value (0-1023) already mapped
    :return: 10-byte packet as bytes
    """
    data = bytearray(10)
    # General information packet type: 1th bit CLEAR, then length 6 bytes (0b110), then packet type 0 (0b000) -> 0x60
    data[0] = 0x60

    # MSB 7 bits of 10-bit speed, direction, and MAX_SPEED
    # Get the 7 MSB of speed (out of 10), and SET the 8th bit to 1
    data[1] = 0x80 | ((speed >> 3) & 0x7F)
    # Get the 7 MSB of direction (out of 10), and SET the 8th bit to 1
    data[2] = 0x80 | ((direction >> 3) & 0x7F)
    # Get the 7 MSB of MAX_SPEED (out of 8), and SET the 8th bit to 1
    data[3] = 0x80 | ((MAX_SPEED >> 1) & 0x7F)

    # LSB packing
    data[4] = (
        0x80  # Set the 8th bit to 1
        | ((MAX_SPEED & 0x01) << 6)  # Get the 1 LSB of MAX_SPEED (out of 8) and place it to the 7th bit
        | ((speed & 0x07) << 3)  # Get the 3 LSB of speed_val (out of 10) and place it to the 4th, 5th, and 6th bits
        | (direction & 0x07)  # Get the 3 LSB of direction_val (out of 10) and place it to the 1st, 2nd, and 3rd bits
    )

    data[5] = 128  # MSB is SET, then horn off, lock off, no errors
    data[6] = 132  # MSB is SET, then deactivate hazard, indicators, calibration and power OFF, but activate potential SPM HPP messages
    data[7] = 128  # MSB is SET, then no fault, no headlights, and setting drive mode

    chksum = (255 - (sum(data[0:8]) & 0x7F)) & 0xFF
    data[8] = chksum

    data[9] = 15  # This is the transmit finish packet! Technically a separate packet
    return bytes(data)

def read_message_from_shark(message: bytes) -> dict[str, float]:
    """
    Read the SPM general information from the message.
    
    :param message: The message to read the SPM general information from
    :return: The SPM general information
    """
    messagetype = (message[0] & 0x0F)
    if messagetype == 1 : # Shark Power Module General Information
        fuel_gauge = (message[1] & 31) # 0 - 18
        ground_speed = (message[7] & 31) # 0 - 31
        return {
            "fuel_gauge": fuel_gauge * 100 / 18,
            "ground_speed": ground_speed / 31 * NOMINAL_MAX_SPEED,
        }
    return {}



def ReceiveMessage(ser: serial.Serial) -> bytes | None:
    """Read bytes from serial port until End-of-Transmission byte is received."""
    message_bytes = bytearray()
    last_hex_value = 0x01
    while last_hex_value != 0x0F:
        data = ser.read(1)
        if not data:
            return None
        hex_value = data[0]
        message_bytes.extend(data)
        last_hex_value = hex_value
    return bytes(message_bytes)


def serial_communication_loop(ser: serial.Serial, wheelchair_state: models.WheelchairCommand, stop_event: threading.Event, spm_general_information: dict[str, float]) -> None:
    """
    Continuous loop to send serial packets.
    
    :param ser: Serial connection
    :param wheelchair_state: Current wheelchair state
    :param stop_event: Event to stop the loop
    """
    while not stop_event.is_set():
        speed_byte = normalization.normalize_range(-1.0, 1.0, 0, 1023, wheelchair_state.speed)
        direction_byte = normalization.normalize_range(-1.0, 1.0, 0, 1023, wheelchair_state.direction)
        ser.write(build_runtime_packet(speed=speed_byte, direction=direction_byte))
        ser.flush()
        spm_general_information_packet = ReceiveMessage(ser)
        if spm_general_information_packet:
            spm_general_information.update(read_message_from_shark(spm_general_information_packet))
        time.sleep(LOOP_WAIT_TIME)


class WheelchairController:
    """Main controller class for wheelchair operations."""
    
    def __init__(self, port: str = "/dev/ttyUSB0") -> None:
        """
        Initialize the wheelchair controller.
        
        :param port: Serial port to connect to
        :param max_idle_time: Maximum idle time in seconds before the controller resets the state to idle.
        """
        self.port = port
        self.serial_connection: serial.Serial | None = None
        self.serial_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.wheelchair_state = models.WheelchairCommand(timestamp=datetime.datetime.now())
        self.spm_general_information: dict[str, float] = {
            'fuel_gauge': 0.0,
            'ground_speed': 0.0,
        }
    
    def start(self) -> bool:
        """Attempt to open the serial port and spawn the TX thread.

        Returns ``True`` when the connection is opened, ``False`` otherwise. The
        method never raises so callers can attempt to connect repeatedly without
        crashing the application.
        """
        if self.serial_connection and self.serial_connection.is_open:
            return True  # already connected

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=0.2,
            )
            print(f"[{self.port}] Serial connection established")

            time.sleep(START_WAIT_TIME)

            self.stop_event.clear()
            self.serial_thread = threading.Thread(
                target=serial_communication_loop,
                args=(self.serial_connection, self.wheelchair_state, self.stop_event, self.spm_general_information),
                daemon=True,
            )
            self.serial_thread.start()
            return True
        except Exception as exc:
            # Connection failed: very likely because the adapter is not plugged
            # in yet. Log and let the caller try again later.
            print(f"[{self.port}] Unable to open serial connection: {exc}")
            self.serial_connection = None
            return False
    
    def stop(self) -> None:
        """Clean up serial connection."""
        if self.serial_connection:
            self.stop_event.set()
            if self.serial_thread:
                self.serial_thread.join(timeout=1.0)
            self.serial_connection.close()
    
    def control(self, speed: float, direction: float) -> None:
        """Set speed and direction for the wheelchair.

        The method transparently (re)establishes the serial connection when it
        is not yet available. If the connection cannot be opened (e.g. the USB
        adapter is still unplugged) the call safely returns without raising and
        without updating *wheelchair_state*.

        :param speed: Desired speed in the 
            range ``-1.0`` (full reverse) .. ``1.0`` (full forward)
        :param direction: Desired steering direction in the
            range ``-1.0`` (full left) .. ``1.0`` (full right)
        """
        # Lazily (re)connect when the port becomes available.
        if not self.serial_connection or not self.serial_connection.is_open:
            if not self.start():
                # Still not connected – skip this command.
                return
        
        self.wheelchair_state.speed = speed
        self.wheelchair_state.direction = direction
        self.wheelchair_state.timestamp = datetime.datetime.now()
    
    def get_status(self) -> dict:
        """
        Get current wheelchair status.
        
        :return: Current speed and direction
        """
        return {
            "speed": self.wheelchair_state.speed,
            "direction": self.wheelchair_state.direction,
            "timestamp": self.wheelchair_state.timestamp.isoformat()
        }

    def get_spm_general_information(self) -> dict[str, float]:
        """
        Get current SPM general information.
        
        :return: Current SPM general information
        """
        return self.spm_general_information