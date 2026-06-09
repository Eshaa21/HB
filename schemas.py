from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateDataRequest(BaseModel):
    """Request body for manually generating one telemetry reading.

    Both fields are optional so Swagger can send an empty body and let the
    system pick a registered pipeline automatically.
    """

    area_name: str | None = Field(default=None, description="Optional area to generate data for")
    pipeline_name: str | None = Field(default=None, description="Optional pipeline to generate data for")


class AlertResponse(BaseModel):
    """API response model for a leak alert row."""

    id: int | None = None
    area_name: str
    pipeline_name: str
    alert_type: str
    severity: str
    message: str
    timestamp: str


class TelemetryResponse(BaseModel):
    """API response model for telemetry, enriched with alert information."""

    id: int
    area_name: str
    pipeline_name: str
    flow_rate: float
    pressure: float
    consumption: float
    timestamp: str
    alert_created: bool = False
    alert: AlertResponse | None = None


class LogResponse(BaseModel):
    """API response wrapper for recent log lines."""

    logs: list[str]


class AreaResponse(BaseModel):
    """Response body for registered areas."""

    id: int
    area_name: str
    created_at: str


class PipelineResponse(BaseModel):
    """Response body for registered pipelines."""

    id: int
    area_name: str
    pipeline_name: str
    created_at: str


class AreaRequest(BaseModel):
    """Request body for creating or deleting an area."""

    area_name: str


class PipelineRequest(BaseModel):
    """Request body for creating or deleting a pipeline."""

    area_name: str
    pipeline_name: str


class PipelineAnalytics(BaseModel):
    """Pipeline-level analytics nested inside an area."""

    pipeline_name: str
    average_flow: float
    average_pressure: float
    average_consumption: float
    leak_count: int


class AreaAnalytics(BaseModel):
    """Area-level analytics returned by GET /analytics."""

    area_name: str
    average_flow: float
    average_pressure: float
    average_consumption: float
    leak_count: int
    pipelines: list[PipelineAnalytics] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    """Top-level analytics response."""

    total_water_flow: float
    total_consumption: float
    water_loss: float
    average_pressure: float
    leak_count: int
    area_wise_statistics: list[AreaAnalytics]
