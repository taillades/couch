import serial

class ThermoSerial:
    """
    Interface for reading temperature data from the Arduino-based
    DallasTemperature/OneWire sensor array via serial connection.

    The Arduino sketch outputs a line of 5 semicolon-separated floats:
    left;right;air;box;battery
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        """
        Initialize the serial connection.

        :param port: Serial port device (e.g., '/dev/ttyUSB0')
        :param baudrate: Baud rate for serial communication
        :param timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
    
    def start(self) -> None:
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        print(f"Connected to {self.port}")

    def read_temperatures(self) -> dict[str, float] | None:
        """
        Read a line from the serial port and parse the temperatures.

        :returns: Tuple of (left, right, air, box, battery) temperatures in Celsius,
                  or None if parsing fails or timeout occurs.
        """
        if self.ser is None:
            return None
        try:
            line = self.ser.readline().decode("utf-8").strip()
            if not line:
                return None
            parts = line.split(";")
            if len(parts) != 5:
                return None
            temps = tuple(float(x) for x in parts)
            return {
                "left": temps[0],
                "right": temps[1],
                "air": temps[2],
                "box": temps[3],
                "battery": temps[4],
            }
        except Exception:
            return None

    def stop(self) -> None:
        """
        Close the serial connection.
        """
        if self.ser is not None:
            self.ser.close()

