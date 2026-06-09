from __future__ import annotations

# This file handles the API endpoint for water analytics
# It returns summary statistics about water flow, pressure, consumption, and leaks

# Import APIRouter to create API endpoints
from fastapi import APIRouter

# Import the function that calculates analytics summary
# Called from: analytics.py generate_analytics_summary function
from analytics import generate_analytics_summary
# Import logging functions to write messages
from logger_config import get_logger
# Import data model for response
from schemas import AnalyticsResponse

# Create a router to handle these endpoints
router = APIRouter(tags=["Analytics"])
# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# This endpoint is called when user wants to see water analytics
@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics() -> dict[str, object]:
    """Return computed analytics and summary statistics from all water data in database
    
    This is called by:
        - User clicks on GET /analytics endpoint in Swagger documentation
        - User sends GET request to /analytics in their application
    
    What this endpoint does:
        1. Calculate summary statistics from all water readings
        2. Calculate average flow rate, pressure, consumption
        3. Calculate water loss (difference between flow and consumption)
        4. Count total number of leaks detected
        5. Break down statistics by area
        6. Break down statistics by pipeline within each area
        7. Return all calculations as a summary
    
    Returns:
        Analytics summary with total stats and area-wise breakdown:
        {
            "total_water_flow": 1000.50,
            "total_consumption": 950.25,
            "water_loss": 50.25,
            "average_pressure": 55.5,
            "leak_count": 5,
            "area_wise_statistics": [
                {
                    "area_name": "Kothrud",
                    "average_flow": 500.25,
                    "average_pressure": 55.0,
                    "average_consumption": 475.12,
                    "leak_count": 2,
                    "pipelines": [
                        {
                            "pipeline_name": "KOTH_P1",
                            "average_flow": 250.0,
                            "average_pressure": 55.5,
                            "average_consumption": 235.0,
                            "leak_count": 1
                        },
                        {
                            "pipeline_name": "KOTH_P2",
                            "average_flow": 250.25,
                            "average_pressure": 54.5,
                            "average_consumption": 240.12,
                            "leak_count": 1
                        }
                    ]
                },
                ...
            ]
        }
    """
    # Write a log message saying someone requested analytics
    logger.info("Analytics requested")
    # Call the analytics function to calculate and return all summary statistics
    return generate_analytics_summary()
