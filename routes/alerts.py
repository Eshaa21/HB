from __future__ import annotations

# This file handles the API endpoint for viewing leak alerts
# It returns all the alerts that were generated when water readings showed a leak

# Import APIRouter to create API endpoints
from fastapi import APIRouter

# Import function to get all alerts from database
# Called from: database.py get_alert_records function
from database import get_alert_records, remove_alert_record
# Import logging functions to write messages
from logger_config import get_logger
# Import data model for response
from schemas import AlertResponse

# Create a router to handle these endpoints
router = APIRouter(tags=["Alerts"])
# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# This endpoint is called when user wants to see all leak alerts
@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts() -> list[dict[str, object]]:
    """Return all stored leak alerts from the system
    
    This is called by:
        - User clicks on GET /alerts endpoint in Swagger documentation
        - User sends GET request to /alerts in their application
    
    What this endpoint does:
        1. Get all leak alerts that were generated
        2. Return list of all alerts
    
    Returns:
        List of all leak alerts with their information:
        [
            {
                "id": 1,
                "area_name": "Kothrud",
                "pipeline_name": "KOTH_P1",
                "alert_type": "Leak Detected",
                "severity": "CRITICAL",
                "message": "Pressure dropped below 40 PSI",
                "timestamp": "2026-06-06T12:30:00+00:00"
            },
            {
                "id": 2,
                "area_name": "Hinjewadi",
                "pipeline_name": "HINJ_P1",
                "alert_type": "Leak Detected",
                "severity": "WARNING",
                "message": "Flow rate is more than consumption by 30 L/Day",
                "timestamp": "2026-06-06T12:35:00+00:00"
            },
            ...
        ]
    """
    # Write a log message saying someone requested the alerts
    logger.info("Alerts requested")
    # Get all leak alerts from database and return them
    return get_alert_records()


@router.delete("/alerts/{alert_id}")
def resolve_alert(alert_id: int) -> dict[str, object]:
    """Remove one alert from the database after it has been resolved."""
    logger.info("Resolve requested for alert %s", alert_id)
    deleted = remove_alert_record(alert_id)
    if not deleted:
        return {"success": False, "detail": "Alert not found"}
    return {"success": True, "detail": "Alert resolved"}
