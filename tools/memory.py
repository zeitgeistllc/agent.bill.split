# tools/memory.py
import json
import os
from langchain.tools import tool

# Define the path to our simple JSON database relative to this file's location
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
JSON_FILE_PATH = os.path.join(DATA_DIR, 'previous_meter_readings.json')

def _load_readings() -> dict:
    """Helper function to load readings from the JSON file."""
    if not os.path.exists(JSON_FILE_PATH):
        # Create the data directory and default file if they don't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(JSON_FILE_PATH, 'w') as f:
            json.dump({"electricity": 0.0, "water": 0.0}, f)
        return {"electricity": 0.0, "water": 0.0}
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"electricity": 0.0, "water": 0.0} # Return default if file is empty or corrupt

def _save_readings(readings: dict):
    """Helper function to save readings to the JSON file."""
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(readings, f, indent=4)

@tool
def get_previous_reading_tool(utility_type: str) -> str:
    """
    Retrieves the last saved meter reading for a specific utility type ('electricity' or 'water').
    """
    utility_type = utility_type.lower()
    if utility_type not in ['electricity', 'water']:
        return "Error: Invalid utility type. Must be 'electricity' or 'water'."

    readings = _load_readings()
    reading = readings.get(utility_type, 0.0)
    return f"Previous reading for {utility_type} is {reading}."

@tool
def save_current_reading_tool(utility_type: str, new_reading: float) -> str:
    """
    Saves the current meter reading for a specific utility type ('electricity' or 'water'),
    overwriting the previous one.
    """
    utility_type = utility_type.lower()
    if utility_type not in ['electricity', 'water']:
        return "Error: Invalid utility type. Must be 'electricity' or 'water'."

    readings = _load_readings()
    readings[utility_type] = new_reading
    _save_readings(readings)
    return f"Successfully saved new {utility_type} reading: {new_reading}."
