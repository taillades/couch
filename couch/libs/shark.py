"""Wheelchair control library for serial communication."""

from typing import Final
import time
import threading
from dataclasses import dataclass

import serial

from couch.libs import normalization

MAX_SPEED: Final[int] = 255
BAUD_RATE: Final[int] = 38400
START_WAIT_TIME: Final[float] = 0.3
LOOP_WAIT_TIME: Final[float] = 0.016


@dataclass
class WheelchairState:
    """Current state of the wheelchair."""
    speed: float = 0.0
    direction: float = 1.0


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


def serial_communication_loop(ser: serial.Serial, wheelchair_state: WheelchairState, stop_event: threading.Event) -> None:
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
        time.sleep(LOOP_WAIT_TIME)


class WheelchairController:
    """Main controller class for wheelchair operations."""
    
    def __init__(self, port: str = "/dev/ttyUSB0") -> None:
        """
        Initialize the wheelchair controller.
        
        :param port: Serial port to connect to
        """
        self.port = port
        self.serial_connection: serial.Serial | None = None
        self.serial_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.wheelchair_state = WheelchairState()
    
    def start(self) -> None:
        """Initialize serial connection and start communication thread."""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=0.2
            )
            print("Started serial communication")
            time.sleep(START_WAIT_TIME)
            
            self.stop_event.clear()
            self.serial_thread = threading.Thread(
                target=serial_communication_loop,
                args=(self.serial_connection, self.wheelchair_state, self.stop_event),
                daemon=True
            )
            self.serial_thread.start()
            
        except Exception as e:
            print(f"Failed to initialize serial connection: {e}")
            raise
    
    def stop(self) -> None:
        """Clean up serial connection."""
        if self.serial_connection:
            self.stop_event.set()
            if self.serial_thread:
                self.serial_thread.join(timeout=1.0)
            self.serial_connection.close()
    
    def control(self, speed: float, direction: float) -> None:
        """
        Control the wheelchair with speed and direction.
        
        :param speed: Speed value between -1.0 and 1.0
        :param direction: Direction value between -1.0 and 1.0
        """
        if not self.serial_connection:
            raise RuntimeError("Serial connection not available")
        
        self.wheelchair_state.speed = speed
        self.wheelchair_state.direction = direction
    
    def get_status(self) -> dict:
        """
        Get current wheelchair status.
        
        :return: Current speed and direction
        """
        return {
            "speed": self.wheelchair_state.speed,
            "direction": self.wheelchair_state.direction
        }
