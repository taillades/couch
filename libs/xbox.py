import threading
import time
import importlib
from typing import Optional, Callable, Dict, Any

import inputs

from libs.speaker import play_music

def play_music_callback(music_file: str) -> None:
    """Callback for play music button."""
    def music_thread():
        play_music(music_file)
    thread = threading.Thread(target=music_thread, daemon=True)
    thread.start()

class XboxRemote:
    """Xbox remote input handler for reading joystick and button states."""
    
    def __init__(self, *, callbacks: Dict[str, Callable[[Any], None]], deadzone: float = 0.1) -> None:
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
        self.button_right_trigger = False
        self.button_left_trigger = False
        self._callbacks = callbacks

        # Deadzone for joystick (to prevent drift)
        self.deadzone = deadzone


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
        if self._thread and self._thread.is_alive():
            # Do not block indefinitely in case the underlying library hangs
            self._thread.join(timeout=1.0)
            
    def _input_loop(self) -> None:
        """Main input processing loop."""
        while self._running:
            try:
                events = inputs.get_gamepad()
                for event in events:
                    self._process_event(event)
            except OSError as e:  # Handle unplugged device separately for reconnection logic
                if e.errno == 19:  # "No such device" – likely unplugged
                    print("Gamepad disconnected. Waiting for reconnection…")
                    self._handle_disconnect()
                    time.sleep(1.0)
                else:
                    print(f"OS error reading gamepad: {e}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error reading gamepad: {e}")
                inputs.devices._find_devices()
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
            elif event.code == 'ABS_HAT0Y':
                # It's a bit weird, but the hat is -1 when up and 1 when down
                if event.state == 0:
                    self.button_up = False
                    self.button_down = False
                elif event.state == -1:
                    self.button_up = True
                    self._trigger_callback('button_up', self.button_up)
                elif event.state == 1:
                    self.button_down = True
                    self._trigger_callback('button_down', self.button_down)
            elif event.code == 'ABS_HAT0X':
                if event.state == 1:
                    self.button_right = True
                    self._trigger_callback('button_right', self.button_right)
                elif event.state == -1:
                    self.button_left = True
                    self._trigger_callback('button_left', self.button_left)
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
            elif event.code == 'BTN_TR':
                self.button_right_trigger = bool(event.state)
                self._trigger_callback('button_right_trigger', self.button_right_trigger)
            elif event.code == 'BTN_TL':
                self.button_left_trigger = bool(event.state)
                self._trigger_callback('button_left_trigger', self.button_left_trigger)
                
    def _normalize_axis(self, value: int) -> float:
        """Normalize axis value from raw input to -1.0 to 1.0 range."""
        normalized = value / 32768.0
        if abs(normalized) < self.deadzone:
            return 0.0
        return max(-1.0, min(1.0, normalized))
        
    def _trigger_callback(self, event_type: str, value: Any) -> None:
        """Trigger the registered callback **only** when the button is actively pressed.

        Release events (``value`` evaluates to :pydata:`False`) are ignored so that
        callbacks correspond to the *action* of pressing the button rather than
        its current pressed state.
        """
        # Execute callback *only* on the press (value == True)
        if value and event_type in self._callbacks:
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
        speed = -self.left_y
        direction = self.left_x
        return speed, direction
        
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
            inputs.get_gamepad()
            return True
        except Exception as e:
            print(f"Error checking connection: {e}")
            return False

    def _handle_disconnect(self) -> None:
        """Attempt to recover from a game-pad disconnection.

        The *inputs* library caches opened device file-descriptors. When the
        controller is physically unplugged those descriptors become invalid
        and every subsequent call to :pyfunc:`inputs.get_gamepad` raises
        ``OSError(19, 'No such device')``. Reloading the *inputs* module forces
        a fresh device scan so that, once the pad is re-plugged, input events
        start flowing again without restarting the whole application.
        """
        try:
            # Reload the module to drop stale file descriptors and rescan
            globals()["inputs"] = importlib.reload(inputs)
            print("Re-initialised input devices – waiting for events…")
        except Exception as e:
            print(f"Error reloading inputs module: {e}")

