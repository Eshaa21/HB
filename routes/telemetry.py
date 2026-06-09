# This file handles API endpoints for water telemetry (sensor readings)
# It has endpoints to generate data, get water data, and see logs

# Import to use decorators and type hints
from __future__ import annotations

# Import FastAPI router to create API endpoints
from fastapi import APIRouter, HTTPException, Query

# Import database functions to get data from database
from database import (
    area_exists,  # check if area exists in database
    get_alert_records,  # get all leak alerts
    get_telemetry_records,  # get all water readings
    normalize_area_name,  # convert area names to standard format
    normalize_pipeline_name,  # convert pipeline names to standard format
    pipeline_exists,  # check if pipeline exists in database
)
# Import logging functions to write messages
from logger_config import get_logger, get_recent_log_entries
# Import data models for request and response
from schemas import GenerateDataRequest, LogResponse, TelemetryResponse
# Import data generation function
from sensor_simulator import generate_sensor_record

# Create a router to handle these endpoints
router = APIRouter(tags=["Telemetry"])
# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# This endpoint is called when user clicks "Generate Data" button in API documentation
@router.post("/generate-data", response_model=TelemetryResponse)
def generate_data(payload: GenerateDataRequest | None = None) -> dict[str, object]:
    """Generate one telemetry reading (water sensor data) manually from Swagger/Postman
    
    This is called by:
        - User clicks "Generate Data" button in Swagger API documentation
        - User sends POST request to /generate-data endpoint
    
    What this endpoint does:
        1. Accept optional request body with area name and pipeline name
        2. If no body provided, let the system pick a random pipeline
        3. Generate one water reading using generate_sensor_record function
        4. Check if the reading indicates a leak
        5. Return the reading and alert info to user

    Args:
        payload: Optional request body containing:
                - area_name: optional area name (like "Kothrud")
                - pipeline_name: optional pipeline name (like "KOTH_P1")
                If empty body, system picks a registered pipeline automatically

    Returns:
        Generated water reading (telemetry) with alert information when a leak is detected
        Example:
        {
            "id": 1,
            "area_name": "Kothrud",
            "pipeline_name": "KOTH_P1",
            "flow_rate": 125.45,
            "pressure": 55.67,
            "consumption": 95.23,
            "timestamp": "2026-06-06T12:30:00+00:00",
            "alert_created": False,
            "alert": None
        }
    """
    # Create a default request body if user didn't provide one
    request = payload or GenerateDataRequest()
    # Write a log message saying someone requested manual data generation
    logger.info("Manual data generation request received")
    # Call the sensor simulator to generate one water reading
    return generate_sensor_record(
        area_name=request.area_name,  # pass the area name if user provided it
        pipeline_name=request.pipeline_name,  # pass the pipeline name if user provided it
    )


# This endpoint is called when user visits /water-data or uses the API
@router.get("/water-data", response_model=list[TelemetryResponse])
def get_water_data(
    area: str | None = Query(default=None, description="Optional area filter"),  # optional area filter
    pipeline: str | None = Query(default=None, description="Optional pipeline filter"),  # optional pipeline filter
) -> list[dict[str, object]]:
    """Return all stored water readings (telemetry) and attach matching leak alerts
    
    This is called by:
        - User clicks on GET /water-data endpoint in Swagger documentation
        - User sends GET request to /water-data in their application
    
    What this endpoint does:
        1. Check if requested area exists in database (if area filter provided)
        2. Check if requested pipeline exists under that area (if pipeline filter provided)
        3. Return 404 error if area or pipeline doesn't exist
        4. Get all water readings from database (optionally filtered by area/pipeline)
        5. Get all leak alerts from database
        6. Combine readings and alerts together
        7. Return list of readings with alert information attached

    Args:
        area: Optional filter - only return readings from this area (like "Kothrud")
              If provided, system checks if area exists
        pipeline: Optional filter - only return readings from this pipeline (like "KOTH_P1")
                 If provided, system checks if pipeline exists under the area

    Returns:
        List of water readings with alert info attached
        Example:
        [
            {
                "id": 1,
                "area_name": "Kothrud",
                "pipeline_name": "KOTH_P1",
                "flow_rate": 125.45,
                "pressure": 55.67,
                "consumption": 95.23,
                "timestamp": "2026-06-06T12:30:00+00:00",
                "alert_created": False,
                "alert": None
            },
            ...
        ]
        
        Raises:
            HTTPException 404: If the requested area doesn't exist
            HTTPException 404: If the requested pipeline doesn't exist under the area
    """
    # Write a log message saying someone requested water data
    logger.info("Water data requested")
    
    # If user provided an area filter, check if the area exists in database
    if area and not area_exists(area):
        # Standardize the area name (like "kothrud" becomes "Kothrud")
        normalized_area = normalize_area_name(area)
        # Return 404 error saying this area doesn't exist
        raise HTTPException(
            status_code=404,  # error code for not found
            detail=f"Area '{normalized_area}' is not available in database",  # error message
        )

    # If user provided both area and pipeline filters, check if the pipeline exists
    if area and pipeline and not pipeline_exists(area, pipeline):
        # Standardize the area name
        normalized_area = normalize_area_name(area)
        # Standardize the pipeline name
        normalized_pipeline = normalize_pipeline_name(pipeline)
        # Return 404 error saying this pipeline doesn't exist under this area
        raise HTTPException(
            status_code=404,  # error code for not found
            detail=f"Pipeline '{normalized_pipeline}' is not available under area '{normalized_area}'",  # error message
        )

    # Get all water readings from database (with optional area/pipeline filters)
    telemetry_records = get_telemetry_records(area=area, pipeline=pipeline)
    # Get all leak alerts from database
    alerts_by_id = {alert["id"]: alert for alert in get_alert_records()}

    # Create a list to store readings with alerts attached
    enriched_records: list[dict[str, object]] = []
    # Go through each water reading
    for record in telemetry_records:
        # Try to find an alert for this reading (using the reading's id)
        alert = alerts_by_id.get(record["id"])
        # Convert the reading to a normal dictionary
        record = dict(record)
        # Mark whether an alert exists for this reading
        record["alert_created"] = alert is not None
        # Add the alert to the reading (or None if no alert)
        record["alert"] = alert
        # Add the reading with alert to the enriched list
        enriched_records.append(record)

    # Return the list of readings with alerts attached
    return enriched_records


# This endpoint is called when user wants to see system logs
@router.get("/logs", response_model=LogResponse)
def get_logs(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, list[str]]:
    """Return recent system log entries from logs/system_logs.log file
    
    This is called by:
        - User clicks on GET /logs endpoint in Swagger documentation
        - User sends GET request to /logs in their application
    
    What this endpoint does:
        1. Accept optional limit parameter (how many log lines to return)
        2. Get the most recent log lines from system_logs.log file
        3. Return the log lines to the user
    
    Args:
        limit: How many recent log lines to return
               - minimum: 1 line
               - maximum: 500 lines
               - default: 100 lines

    Returns:
        Dictionary with list of log lines:
        {
            "logs": [
                "2026-06-06 12:30:00 - INFO - Data generated for Kothrud/KOTH_P1",
                "2026-06-06 12:30:05 - WARNING - Pressure dropped below 40 PSI",
                ...
            ]
        }
    """
    # Write a log message saying someone requested logs
    logger.info("Logs requested")
    # Get the recent log lines from the log file and return them
    return {"logs": get_recent_log_entries(limit)}
