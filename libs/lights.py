from typing import Literal
import serial


Side = Literal["left", "right"]

class LightsSerial:
    """Interface for controlling the lights on the couch."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        """
        Initialize the serial connection.

        :param port: Serial port device (e.g., '/dev/ttyUSB0')
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
    
    def start(self) -> None:
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        print(f"Connected to {self.port}")

    def set_lights(self, side: Side, state: bool) -> None:
        """Set the lights on the couch."""
        if self.ser is None:
            return
        try:
            self.ser.write(f"{side} {state}\n".encode("utf-8"))
        except Exception:
            pass

    def stop(self) -> None:
        if self.ser is not None:
            self.ser.close()

