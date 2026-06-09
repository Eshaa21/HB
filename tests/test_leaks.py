from __future__ import annotations

from database import get_connection, initialize_database
from leak_detector import detect_leak, evaluate_leak_rules
from sensor_simulator import generate_sensor_record


def test_leak_detection_rules_trigger(isolated_environment):
    rules = evaluate_leak_rules(flow_rate=150, pressure=30, consumption=90, previous_pressure=60)

    assert len(rules) >= 2
    assert any(rule["rule"] == "Rule 1" for rule in rules)


def test_alert_creation_on_leak(isolated_environment):
    leak_record = {
        "area_name": "Kothrud",
        "pipeline_name": "KOTH_P1",
        "flow_rate": 170,
        "pressure": 25,
        "consumption": 90,
        "timestamp": "2026-06-06T00:00:00+00:00",
    }

    alert = detect_leak(leak_record, previous_pressure=65)

    assert alert is not None
    assert alert["area_name"] == "Kothrud"
    assert alert["pipeline_name"] == "KOTH_P1"
    assert alert["severity"] == "CRITICAL"


def test_alert_record_saved_via_generation(isolated_environment, monkeypatch):
    import sensor_simulator

    initialize_database()

    monkeypatch.setattr(
        sensor_simulator,
        "generate_sensor_values",
        lambda: {"flow_rate": 170, "pressure": 25, "consumption": 90},
    )
    sensor_simulator.generate_sensor_record(area_name="Wakad", pipeline_name="WAK_P1")

    with get_connection() as connection:
        alert_count = connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    assert alert_count >= 1
