"""Simple server that reads joystick speed via HTTP requests and prints it every second."""

import time
import threading
import requests
from typing import Optional


class JoystickObserver:
    """Observer that reads joystick speed via HTTP requests and prints it periodically."""
    
    def __init__(self, joystick_server_url: str) -> None:
        """Initialize the joystick observer.
        
        Args:
            joystick_server_url: URL of the joystick server
        """
        self.server_url = joystick_server_url
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
    def start(self) -> None:
        """Start the observer."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._observer_loop, daemon=True)
        self._thread.start()
        print("Joystick observer started")
        
    def stop(self) -> None:
        """Stop the observer."""
        self._running = False
        if self._thread:
            self._thread.join()
        print("Joystick observer stopped")
        
    def _get_joystick_data(self) -> Optional[dict]:
        """Get joystick data from the server.
        
        Returns:
            Dictionary with joystick data or None if request failed
        """
        try:
            response = requests.get(f"{self.server_url}/joystick/speed-direction", timeout=1.0)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Server returned status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to joystick server: {e}")
            return None
        
    def _observer_loop(self) -> None:
        """Main observer loop that prints joystick speed every second."""
        while self._running:
            data = self._get_joystick_data()
            
            if data:
                print(data)
            else:
                print("No joystick data available")
                
            time.sleep(0.1)


def run_server(server_url: str) -> None:
    """Run the joystick observer.
    
    Args:
        server_url: URL of the joystick server to connect to
    """
    observer = JoystickObserver(server_url)
    
    try:
        observer.start()
        print(f"Joystick observer started. Connecting to {server_url}")
        print("Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        while True:
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nStopping joystick observer...")
        observer.stop()

