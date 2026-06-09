# This file generates fake water sensor readings every 30 seconds
# It creates flow_rate, pressure, and consumption values
# The data is then checked for leaks and stored in the database

# Import to use decorators and type hints
from __future__ import annotations

# Import random to create random sensor values
import random
# Import datetime and timezone to add timestamps to data
from datetime import datetime, timezone

# Import database functions to store the generated data
from database import (
    add_pipeline,  # add a new water pipeline if it doesn't exist
    get_latest_telemetry_for_pipeline,  # get the last reading for a pipeline
    get_pipelines,  # get all registered pipelines
    insert_alert_record,  # save leak alerts to database
    insert_telemetry_record,  # save water readings to database
    normalize_area_name,  # convert area names to standard format
    normalize_pipeline_name,  # convert pipeline names to standard format
)
# Import leak detection function to check if water readings show a leak
from leak_detector import detect_leak
# Import logging to write messages about what this file is doing
from logger_config import get_logger

# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# Helper function to create one random sensor value between minimum and maximum
def _random_value(minimum: float, maximum: float) -> float:
    """Generate one rounded sensor value inside a range
    
    This is called by: generate_sensor_values function in this file
    
    Args:
        minimum: Lowest allowed value the sensor can read
        maximum: Highest allowed value the sensor can read

    Returns:
        Random float rounded to two decimals (like 45.67)
    """
    # Create random number between minimum and maximum, round to 2 decimal places
    return round(random.uniform(minimum, maximum), 2)


# Create random water sensor readings without any special conditions
def generate_sensor_values() -> dict[str, float]:
    """Generate random IoT sensor values without any manual condition input
    
    This is called by: generate_sensor_record function in this file
    
    Returns:
        Dictionary with three water sensor readings:
        - flow_rate: how much water is flowing (90 to 180)
        - pressure: water pressure in pipes (20 to 70)
        - consumption: how much water is being used (80 to 130)
    """
    # Return a dictionary with three random sensor readings
    return {
        # Generate flow rate value between 90 and 180 using helper function
        "flow_rate": _random_value(90, 180),
        # Generate pressure value between 20 and 70 using helper function
        "pressure": _random_value(20, 70),
        # Generate consumption value between 80 and 130 using helper function
        "consumption": _random_value(80, 130),
    }


# Helper function to pick which area and pipeline to generate data for
def _choose_pipeline(
    area_name: str | None = None,  # optional area name from API request
    pipeline_name: str | None = None,  # optional pipeline name from API request
) -> tuple[str, str]:
    """Resolve the area and pipeline for one telemetry generation request
    
    This is called by: generate_sensor_record function in this file
    
    If user specifies both area and pipeline:
        - Use the ones they requested
        - Add the pipeline to database if it's new
    
    If no pipelines exist:
        - Create default ones like "Kothrud" area with "KOTH_P1" pipeline
    
    If some pipelines exist:
        - Pick one randomly to generate data for

    Args:
        area_name: Optional area name from API (like "Kothrud")
        pipeline_name: Optional pipeline name from API (like "KOTH_P1")

    Returns:
        Tuple of (normalized_area_name, normalized_pipeline_name)
    """
    # If user provided both area and pipeline names
    if area_name and pipeline_name:
        # Convert area name to standard format (like "kothrud" becomes "Kothrud")
        normalized_area = normalize_area_name(area_name)
        # Convert pipeline name to standard format (like "koth-p1" becomes "KOTH_P1")
        normalized_pipeline = normalize_pipeline_name(pipeline_name)
        # Add this pipeline to database if it doesn't exist
        add_pipeline(normalized_area, normalized_pipeline)
        # Return the standardized names
        return normalized_area, normalized_pipeline

    # Get all registered pipelines from database
    pipelines = get_pipelines(area=area_name)
    # If no pipelines exist in database
    if not pipelines:
        # Create default area name - use provided one or default to "Kothrud"
        normalized_area = normalize_area_name(area_name or "Kothrud")
        # Create default pipeline name - like "KOTH_P1" for Kothrud area
        normalized_pipeline = normalize_pipeline_name(pipeline_name or f"{normalized_area[:4]}_P1")
        # Add this default pipeline to database
        add_pipeline(normalized_area, normalized_pipeline)
        # Return the default names
        return normalized_area, normalized_pipeline

    # Get a random pipeline from the list of registered pipelines
    chosen_pipeline = random.choice(pipelines)
    # Return the random pipeline's area and name
    return chosen_pipeline["area_name"], chosen_pipeline["pipeline_name"]


# Create one fake water sensor reading and check for leaks
def generate_sensor_record(
    area_name: str | None = None,  # optional area name
    pipeline_name: str | None = None,  # optional pipeline name
) -> dict[str, object]:
    """Generate, store, and evaluate one telemetry record (water reading)
    
    This is called by:
        1. generate_all_pipeline_data function in this file (scheduler every 30 seconds)
        2. /generate-data endpoint in routes/telemetry.py (when user clicks button)

    What this function does:
        1. Pick which pipeline to generate data for
        2. Get the last pressure reading for that pipeline (to detect sudden drops)
        3. Create random sensor values (flow_rate, pressure, consumption)
        4. Add timestamp
        5. Save the reading to database
        6. Check if readings indicate a leak using leak detection rules
        7. If leak detected, save alert to database
        8. Return the reading and alert info to caller

    Args:
        area_name: Optional area name - if not given, pick a random pipeline
        pipeline_name: Optional pipeline name - if not given, pick a random pipeline

    Returns:
        Dictionary with water reading and alert info:
        {
            "area_name": "Kothrud",
            "pipeline_name": "KOTH_P1",
            "flow_rate": 125.45,
            "pressure": 55.67,
            "consumption": 95.23,
            "timestamp": "2026-06-06T12:30:00+00:00",
            "id": 1,
            "alert_created": False or True,
            "alert": None or alert_dict
        }
    """
    # Pick which area and pipeline to use (either from arguments or pick randomly)
    area_name, pipeline_name = _choose_pipeline(area_name=area_name, pipeline_name=pipeline_name)

    # Get the last water reading for this pipeline from database (needed for leak detection)
    # This is used to check if pressure suddenly drops (Rule 3)
    previous_record = get_latest_telemetry_for_pipeline(area_name, pipeline_name)
    # Get the pressure value from the last reading (or None if this is first reading)
    previous_pressure = float(previous_record["pressure"]) if previous_record else None
    # Create random sensor readings
    generated_values = generate_sensor_values()
    # Get current date and time with timezone
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create a dictionary with the new sensor reading
    record: dict[str, object] = {
        "area_name": area_name,  # which area this reading is from
        "pipeline_name": pipeline_name,  # which pipeline this reading is from
        "flow_rate": generated_values["flow_rate"],  # how much water is flowing
        "pressure": generated_values["pressure"],  # water pressure in pipes
        "consumption": generated_values["consumption"],  # how much water is being used
        "timestamp": timestamp,  # when this reading was taken
    }

    # Save the water reading to database and get the id
    telemetry_id = insert_telemetry_record(record)
    # Add the id to the record dictionary
    record["id"] = telemetry_id
    # Write a log message saying data was created
    logger.info("Data generated for %s/%s", area_name, pipeline_name)

    # Check if this reading indicates a leak using the leak detection rules
    alert = detect_leak(record, previous_pressure=previous_pressure)
    # If a leak was detected (alert is not None)
    if alert:
        # Save the alert to database and get its id
        alert_id = insert_alert_record(alert, telemetry_id=telemetry_id)
        # Add the id to the alert dictionary
        alert["id"] = alert_id
        # Mark that an alert was created
        record["alert_created"] = True
        # Add the alert information to the record
        record["alert"] = alert
        # Write a warning log message saying a leak alert was created
        logger.critical("Alert generated for %s/%s", area_name, pipeline_name)
    # If no leak detected
    else:
        # Mark that no alert was created
        record["alert_created"] = False
        # Set alert to None (no alert)
        record["alert"] = None

    # Return the water reading and alert info back to the caller
    return record


# Generate water readings for all registered pipelines (called every 30 seconds)
def generate_all_pipeline_data() -> list[dict[str, object]]:
    """Generate one telemetry record for every registered pipeline
    
    This is called by:
        BackgroundScheduler in main.py every 30 seconds (from lifespan function)

    What this function does:
        1. Get all registered pipelines from database
        2. For each pipeline, generate one water reading
        3. Each reading is checked for leaks
        4. Return list of all generated readings
    
    With default Pune data it creates 8 telemetry readings per cycle
    (4 areas × 2 pipelines each = 8 readings)

    Returns:
        List of generated telemetry records (water readings and alerts)
    """
    # Create empty list to store all the generated readings
    records = []
    # Get all registered pipelines from database
    for pipeline in get_pipelines():
        # For each pipeline, generate one water reading
        records.append(
            # Call generate_sensor_record to create reading for this specific pipeline
            generate_sensor_record(
                area_name=pipeline["area_name"],  # use the pipeline's area
                pipeline_name=pipeline["pipeline_name"],  # use the pipeline's name
            )
        )

    # Write a log message showing how many readings were created
    logger.info("Automatic data generation cycle completed with %s records", len(records))
    # Return the list of all generated readings
    return records
