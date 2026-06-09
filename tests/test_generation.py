from __future__ import annotations

from database import get_connection, initialize_database
from sensor_simulator import generate_all_pipeline_data, generate_sensor_record, generate_sensor_values


def test_database_creation(isolated_environment):
    initialize_database()

    with get_connection() as connection:
        areas = connection.execute("SELECT COUNT(*) FROM areas").fetchone()[0]
        pipelines = connection.execute("SELECT COUNT(*) FROM pipelines").fetchone()[0]
        telemetry = connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
        alerts = connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        telemetry_columns = [
            row["name"] for row in connection.execute("PRAGMA table_info(telemetry)").fetchall()
        ]

    assert areas == 4
    assert pipelines == 8
    assert telemetry == 0
    assert alerts == 0
    assert "status" not in telemetry_columns


def test_synthetic_data_generation(isolated_environment):
    initialize_database()
    record = generate_sensor_record(area_name="Kothrud", pipeline_name="KOTH_P1")

    assert record["area_name"] == "Kothrud"
    assert record["pipeline_name"] == "KOTH_P1"
    assert record["id"] > 0

    with get_connection() as connection:
        stored = connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]

    assert stored == 1


def test_new_area_and_pipeline_are_registered_during_generation(isolated_environment):
    initialize_database()
    record = generate_sensor_record(area_name="Aundh", pipeline_name="AUND_P1")

    assert record["area_name"] == "Aundh"
    assert record["pipeline_name"] == "AUND_P1"

    with get_connection() as connection:
        area_count = connection.execute("SELECT COUNT(*) FROM areas WHERE area_name = 'Aundh'").fetchone()[0]
        pipeline_count = connection.execute(
            "SELECT COUNT(*) FROM pipelines WHERE area_name = 'Aundh' AND pipeline_name = 'AUND_P1'"
        ).fetchone()[0]

    assert area_count == 1
    assert pipeline_count == 1


def test_generate_sensor_values_ranges(isolated_environment):
    values = generate_sensor_values()

    assert 90 <= values["flow_rate"] <= 180
    assert 20 <= values["pressure"] <= 70
    assert 80 <= values["consumption"] <= 130


def test_generate_all_pipeline_data_creates_eight_records(isolated_environment):
    initialize_database()
    records = generate_all_pipeline_data()

    assert len(records) == 8
    with get_connection() as connection:
        stored = connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]

    assert stored == 8
