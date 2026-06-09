from __future__ import annotations

from analytics import generate_analytics_summary
from database import initialize_database
from sensor_simulator import generate_sensor_record


def test_analytics_calculations(isolated_environment):
    initialize_database()
    generate_sensor_record(area_name="Kothrud", pipeline_name="KOTH_P1")
    generate_sensor_record(area_name="Hinjewadi", pipeline_name="HINJ_P1")
    generate_sensor_record(area_name="Baner", pipeline_name="BAN_P1")

    analytics = generate_analytics_summary()

    assert analytics["total_water_flow"] > 0
    assert analytics["total_consumption"] > 0
    assert analytics["average_pressure"] > 0
    assert len(analytics["area_wise_statistics"]) == 4
    assert all("pipelines" in area for area in analytics["area_wise_statistics"])


def test_api_endpoints(app_client, isolated_environment):
    health = app_client.get("/")
    assert health.status_code == 200
    assert health.json()["status"] == "Running"

    generated = app_client.post(
        "/generate-data",
        json={"area_name": "Kothrud", "pipeline_name": "KOTH_P1"},
    )
    assert generated.status_code == 200
    assert generated.json()["area_name"] == "Kothrud"
    assert generated.json()["pipeline_name"] == "KOTH_P1"
    assert "status" not in generated.json()

    created_by_telemetry = app_client.post(
        "/generate-data",
        json={"area_name": "Aundh", "pipeline_name": "AUND_P1"},
    )
    assert created_by_telemetry.status_code == 200
    assert created_by_telemetry.json()["area_name"] == "Aundh"
    assert created_by_telemetry.json()["pipeline_name"] == "AUND_P1"

    pipelines = app_client.get("/pipelines?area=Aundh")
    assert pipelines.status_code == 200
    assert any(pipeline["pipeline_name"] == "AUND_P1" for pipeline in pipelines.json())

    water_data = app_client.get("/water-data?area=Kothrud&pipeline=KOTH_P1")
    assert water_data.status_code == 200
    assert isinstance(water_data.json(), list)

    missing_area = app_client.get("/water-data?area=Snagar&pipeline=S2")
    assert missing_area.status_code == 404
    assert "not available in database" in missing_area.json()["detail"]

    missing_pipeline = app_client.get("/water-data?area=Kothrud&pipeline=NO_PIPE")
    assert missing_pipeline.status_code == 404
    assert "not available under area" in missing_pipeline.json()["detail"]

    alerts = app_client.get("/alerts")
    assert alerts.status_code == 200

    analytics = app_client.get("/analytics")
    assert analytics.status_code == 200
    assert "area_wise_statistics" in analytics.json()

    logs = app_client.get("/logs")
    assert logs.status_code == 200
    assert isinstance(logs.json()["logs"], list)
