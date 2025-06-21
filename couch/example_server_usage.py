"""Example usage of the wheelchair controller through the server API."""

import time
import requests
from typing import Dict, Any


def send_command(speed: float, direction: float) -> Dict[str, Any]:
    """
    Send a command to the wheelchair controller server.
    
    :param speed: Speed value between -1.0 and 1.0
    :param direction: Direction value between -1.0 and 1.0
    :return: Server response
    """
    url = "http://localhost:8000/control"
    data = {"speed": speed, "direction": direction}
    
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()


def get_status() -> Dict[str, Any]:
    """
    Get current wheelchair status from the server.
    
    :return: Current status
    """
    url = "http://localhost:8000/status"
    
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Demonstrate usage of the wheelchair controller through the server API."""
    print("Wheelchair Controller Server Example")
    print("=" * 40)
    
    try:
        # Check initial status
        print("Getting initial status...")
        status = get_status()
        print(f"Initial status: {status}")
        
        # Move forward at half speed
        print("\nMoving wheelchair forward at half speed...")
        response = send_command(speed=0.0, direction=0.0)
        print(f"Command response: {response}")
        time.sleep(2)
        
        # # Stop
        # print("\nStopping wheelchair...")
        # response = send_command(speed=0.0, direction=1.0)
        # print(f"Command response: {response}")
        # time.sleep(1)
        
        # # Move backward at quarter speed
        # print("\nMoving wheelchair backward at quarter speed...")
        # response = send_command(speed=-0.25, direction=-1.0)
        # print(f"Command response: {response}")
        # time.sleep(2)
        
        # # Stop
        # print("\nStopping wheelchair...")
        # response = send_command(speed=0.0, direction=1.0)
        # print(f"Command response: {response}")
        
        # # Get final status
        # print("\nGetting final status...")
        # status = get_status()
        # print(f"Final status: {status}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server.")
        print("Make sure the server is running with: python -m couch.server.wheelchair")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main() 