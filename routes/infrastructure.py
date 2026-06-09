# This file handles API endpoints for managing areas and pipelines
# Areas are regions like "Kothrud", and pipelines are water pipes under each area

# Import to use decorators and type hints
from __future__ import annotations

# Import FastAPI router to create API endpoints
from fastapi import APIRouter, HTTPException, Query

# Import database functions
from database import (
    add_area,
    add_pipeline,
    area_exists,
    get_areas,
    get_pipelines,
    normalize_area_name,
    remove_area,
    remove_pipeline,
)
# Import logging functions to write messages
from logger_config import get_logger
# Import data models for response
from schemas import AreaRequest, AreaResponse, PipelineRequest, PipelineResponse

# Create a router to handle these endpoints
router = APIRouter(tags=["Infrastructure"])
# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# This endpoint is called when user wants to see all areas
@router.get("/areas", response_model=list[AreaResponse])
def list_areas() -> list[dict[str, object]]:
    """Return all registered water distribution areas (like Kothrud, Hinjewadi, etc)
    
    This is called by:
        - User clicks on GET /areas endpoint in Swagger documentation
        - User sends GET request to /areas in their application
    
    What this endpoint does:
        1. Get all areas from database
        2. Return list of areas
    
    Returns:
        List of all registered areas with their info:
        [
            {
                "id": 1,
                "area_name": "Kothrud",
                "created_at": "2026-06-06T12:30:00+00:00"
            },
            {
                "id": 2,
                "area_name": "Hinjewadi",
                "created_at": "2026-06-06T12:30:00+00:00"
            },
            ...
        ]
    """
    # Write a log message saying someone requested the list of areas
    logger.info("Areas requested")
    # Get and return all registered areas from database
    return get_areas()


@router.post("/areas", response_model=AreaResponse)
def create_area(payload: AreaRequest) -> dict[str, object]:
    """Create an area or return it if it already exists."""
    logger.info("Area create requested: %s", payload.area_name)
    return add_area(payload.area_name)


@router.delete("/areas")
def delete_area(payload: AreaRequest) -> dict[str, object]:
    """Delete an area and related records."""
    logger.info("Area delete requested: %s", payload.area_name)
    deleted = remove_area(payload.area_name)
    if not deleted:
        normalized_area = normalize_area_name(payload.area_name)
        raise HTTPException(status_code=404, detail=f"Area '{normalized_area}' is not available in database")
    return {"deleted": True}


# This endpoint is called when user wants to see all pipelines
@router.get("/pipelines", response_model=list[PipelineResponse])
def list_pipelines(
    area: str | None = Query(default=None, description="Optional area filter"),  # optional area filter
) -> list[dict[str, object]]:
    """Return all registered water pipelines, optionally filtered by area
    
    This is called by:
        - User clicks on GET /pipelines endpoint in Swagger documentation
        - User sends GET request to /pipelines in their application
    
    What this endpoint does:
        1. Check if requested area exists in database (if area filter provided)
        2. If area provided but doesn't exist, return 404 error
        3. Get all pipelines from database (with optional area filter)
        4. Return list of pipelines
    
    Args:
        area: Optional filter - only return pipelines under this area
              If provided, system checks if area exists
              If not provided, returns all pipelines from all areas

    Returns:
        List of pipelines with their info:
        [
            {
                "id": 1,
                "area_name": "Kothrud",
                "pipeline_name": "KOTH_P1",
                "created_at": "2026-06-06T12:30:00+00:00"
            },
            {
                "id": 2,
                "area_name": "Kothrud",
                "pipeline_name": "KOTH_P2",
                "created_at": "2026-06-06T12:30:00+00:00"
            },
            ...
        ]
        
        Raises:
            HTTPException 404: If the requested area doesn't exist in database
    """
    # Write a log message saying someone requested the list of pipelines
    logger.info("Pipelines requested")
    
    # If user provided an area filter, check if the area exists in database
    if area and not area_exists(area):
        # Standardize the area name (like "kothrud" becomes "Kothrud")
        normalized_area = normalize_area_name(area)
        # Return 404 error saying this area doesn't exist
        raise HTTPException(
            status_code=404,  # error code for not found
            detail=f"Area '{normalized_area}' is not available in database",  # error message
        )
    # Get and return all pipelines from database (with optional area filter)
    return get_pipelines(area=area)


@router.post("/pipelines", response_model=PipelineResponse)
def create_pipeline(payload: PipelineRequest) -> dict[str, object]:
    """Create a pipeline under an area."""
    logger.info("Pipeline create requested: %s/%s", payload.area_name, payload.pipeline_name)
    return add_pipeline(payload.area_name, payload.pipeline_name)


@router.delete("/pipelines")
def delete_pipeline(payload: PipelineRequest) -> dict[str, object]:
    """Delete a pipeline and related records."""
    logger.info("Pipeline delete requested: %s/%s", payload.area_name, payload.pipeline_name)
    deleted = remove_pipeline(payload.area_name, payload.pipeline_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline is not available in database")
    return {"deleted": True}
