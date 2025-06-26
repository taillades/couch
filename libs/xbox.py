import threading
import time
from typing import Optional, Callable, Dict, Any
from inputs import get_gamepad


class XboxRemote:
    """Xbox remote input handler for reading joystick and button states."""
    
    def __init__(self) -> None:
        """Initialize the Xbox remote handler."""
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Joystick state (left stick)
        self.left_x = 0.0  # -1.0 to 1.0
        self.left_y = 0.0  # -1.0 to 1.0
        self.right_x = 0.0  # -1.0 to 1.0
        self.right_y = 0.0  # -1.0 to 1.0
        
        # Button states
        self.button_a = False
        self.button_b = False
        self.button_x = False
        self.button_y = False
        self.button_up = False
        self.button_down = False
        self.button_left = False
        self.button_right = False
        self.button_start = False
        
        
        # Callbacks
        self._callbacks: Dict[str, Callable] = {}
        
        # Deadzone for joystick (to prevent drift)
        self.deadzone = 0.1
        
    def start(self) -> None:
        """Start listening for remote input in a separate thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        """Stop listening for remote input."""
        self._running = False
        if self._thread:
            self._thread.join()
            
    def _input_loop(self) -> None:
        """Main input processing loop."""
        while self._running:
            try:
                events = get_gamepad()
                for event in events:
                    self._process_event(event)
            except Exception as e:
                print(f"Error reading gamepad: {e}")
                time.sleep(0.1)
                
    def _process_event(self, event) -> None:
        """Process a single input event."""
        if event.ev_type == 'Absolute':
            if event.code == 'ABS_X':
                self.left_x = self._normalize_axis(event.state)
            elif event.code == 'ABS_Y':
                self.left_y = self._normalize_axis(event.state)
            elif event.code == 'ABS_RX':
                self.right_x = self._normalize_axis(event.state)
            elif event.code == 'ABS_RY':
                self.right_y = self._normalize_axis(event.state)
        elif event.ev_type == 'Key':
            if event.code == 'BTN_SOUTH':   
                self.button_a = bool(event.state)
                self._trigger_callback('button_a', self.button_a)
            elif event.code == 'BTN_EAST':
                self.button_b = bool(event.state)
                self._trigger_callback('button_b', self.button_b)
            elif event.code == 'BTN_WEST':
                self.button_x = bool(event.state)
                self._trigger_callback('button_x', self.button_x)
            elif event.code == 'BTN_NORTH':
                self.button_y = bool(event.state)
                self._trigger_callback('button_y', self.button_y)
            elif event.code == 'BTN_SELECT':
                self.button_start = bool(event.state)
                self._trigger_callback('button_start', self.button_start)
            elif event.code == 'BTN_START':
                self.button_start = bool(event.state)
                self._trigger_callback('button_start', self.button_start)
            elif event.code == 'BTN_MODE':
                self.button_up = bool(event.state)
                self._trigger_callback('button_up', self.button_up)
            elif event.code == 'BTN_SELECT':
                self.button_down = bool(event.state)
                self._trigger_callback('button_down', self.button_down)
            elif event.code == 'BTN_SELECT':
                self.button_left = bool(event.state)
                self._trigger_callback('button_left', self.button_left)
            elif event.code == 'BTN_SELECT':
                self.button_right = bool(event.state)
                self._trigger_callback('button_right', self.button_right)
                
    def _normalize_axis(self, value: int) -> float:
        """Normalize axis value from raw input to -1.0 to 1.0 range."""
        normalized = value / 32768.0
        if abs(normalized) < self.deadzone:
            return 0.0
        return max(-1.0, min(1.0, normalized))
        
    def _trigger_callback(self, event_type: str, value: Any) -> None:
        """Trigger callback for button events."""
        if event_type in self._callbacks:
            try:
                self._callbacks[event_type](value)
            except Exception as e:
                print(f"Error in callback for {event_type}: {e}")

    def get_joystick_xy(self) -> tuple[float, float]:
        """
        Get raw X and Y joystick values.
        
        Returns:
            tuple: (x, y) values in -1.0 to 1.0 range
        """
        return self.left_x, self.left_y
    
    def get_joystick_speed_direction(self) -> tuple[float, float]:
        """
        Get speed and direction from left joystick.
        
        Returns:
            tuple: (speed, direction) where speed is x and direction is y
        """
        return self.left_y, self.left_x
        
    def add_button_callback(self, button: str, callback: Callable) -> None:
        """
        Add a callback function for button events.
        
        Args:
            button: Button name ('button_a' or 'button_b')
            callback: Function to call when button state changes
        """
        self._callbacks[button] = callback
        
    def remove_button_callback(self, button: str) -> None:
        """
        Remove a button callback.
        
        Args:
            button: Button name to remove callback for
        """
        if button in self._callbacks:
            del self._callbacks[button]
            
    def is_connected(self) -> bool:
        """
        Check if remote is connected and responding.
        
        Returns:
            bool: True if remote is connected
        """
        try:
            # Try to get events to test connection
            get_gamepad()
            return True
        except Exception as e:
            print(f"Error checking connection: {e}")
            return False

