import datetime
import serial

ser = serial.Serial('/dev/ttyUSB0', baudrate=38400, bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO,)


def DecodeMessage( message: bytes, verbose: bool = False, verbose_joystick: bool = False) -> int:
    """Decode received message into human readable form."""
    if verbose:
        print(f"Received at: {datetime.datetime.now()}")
        print(' '.join(f"{b:02X}" for b in message))
    
    if len(message) == 0:
        return 0
    
    if message[0] == 0:
        if verbose:
            print("Framing/Power-on startup message - Chomp")
            message = message[1:]
        
    if message[0] > 127 or message[0] == 15:
        if verbose:
            print("Not at message start")
        return 0
        
    
    message_type = message[0] & 0x0F
    if message_type == 2:
        print(message)
        if len(message) > 4:
            speed, direction = decode_joystick_movement(message)
            if verbose_joystick:
                print(f"Speed: {speed}, Direction: {direction}")
            return 0

    if message_type == 2 and verbose: # SR HHP Data
        print("SR HHP Data")

    if message_type == 3 and verbose: # SPM HHP Data
        print("SPM HHP Data")

    if message_type == 4 and verbose: # SR Power Up Information
        print("SR Power Up Information")
        remote_type = message[1] & 0x7F
        year_of_manufacture = 2000 + (message[2] & 0x7F)
        month_of_manufacture = message[3] & 0x0F
        serial_number = ((message[4] & 0x7F) << 14) + ((message[5] & 0x7F) << 7) + (message[6] & 0x7F)
        software_major = (message[7] & 0x38) >> 3
        software_minor = message[7] & 0x07
        capabilities = message[8] & 0x7F
        print("Remote Type:", remote_type)
        print("Manufactured:", month_of_manufacture, "/", year_of_manufacture)
        print("Serial:", serial_number)
        print("Software:" + str(software_major) + "." + str(software_minor))
        print("Capabilites:", capabilities)

    if message_type == 5 and verbose: # SPM Power Up Information
        print("SPM Power Up Information")
        capabilities = message[1] & 0x7F
        print("Capabilities:", capabilities)

    if message_type == 6 and verbose: # Joystick Calibration
        print("Joystick Calibration (SR or ACU)")

    if message_type == 7 and verbose: # Factory Test
        print("Factory Test")

    if message_type == 8 and verbose: # SACU General Information
        print("SACU General Information")

    if message_type == 9 and verbose: # SACU Power Up Information
        print("SACU Power Up Information")

    if message_type == 10 and verbose: # SPM Programmable Settings
        print("SPM Programmable Settings")


    return message_type

def decode_joystick_movement(data_payload: bytes) -> tuple[int, int]:
    """Extract joystick speed and direction readings from SR General Information packet.

    Args:
        data_payload: The data bytes of the SR General Information packet

    Returns:
        Tuple of (speed, direction) where:
        - speed: 0-1023 (512 is center, >512 is forward, <512 is reverse)
        - direction: 0-1023 (512 is center, >512 is right, <512 is left)
    """
    
    speed_msb = (~data_payload[0] & 0x7F) << 3
    speed_lsb = (~data_payload[2] & 0b00111000) >> 3

    speed = speed_msb | speed_lsb
    # print(bin(speed_msb).zfill(7), bin(speed_lsb).zfill(3), bin(speed).zfill(10), len(bin(speed)))
    print(speed, speed_msb, speed_lsb)
    return speed, 0


def ReceiveMessage(ser: serial.Serial) -> bytes:
    """Read bytes from serial port until End-of-Transmission byte is received."""
    message_bytes = bytearray()
    last_hex_value = 0x01
    while last_hex_value != 0x00:
        data = ser.read(1)
        hex_value = data[0]
        message_bytes.extend(data)
        last_hex_value = hex_value
    return bytes(message_bytes)

def SendMessage(ser: serial.Serial, message_type: int, message: bytes) -> None:
    """Send a SharkBus message over serial port.
    
    Args:
        ser: Serial port connection
        message_type: Type of message (0-15)
        message: Payload bytes to send
    """
    message_length = len(message) - 1
    start_byte = bytes([(message_length << 4) + message_type])
    message = start_byte + message
    
    parity = sum(b & 0x7F for b in message) & 0x7F
    parity_byte = bytes([255 - parity])
    eot_byte = bytes([0x00])
    
    message = message + parity_byte + eot_byte
    ser.write(message)



counter = 0
while True:
    message_bytes = ReceiveMessage(ser)
    MessageType = DecodeMessage(message_bytes, verbose=1, verbose_joystick=True)
    # SendMessage(ser, 2, bytes([0x12, 0xC0, 0xC4, 0x2C, 0xF9, 0xDC, 0xFC, 0xBC, 0x11, 0x00]))
