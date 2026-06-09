from __future__ import annotations

# Import sys so modules can be cleared between tests.
import sys

# Import pytest for fixture support.
import pytest


# Provide an isolated database and log environment for each test.
@pytest.fixture()
def isolated_environment(tmp_path, monkeypatch):
    # Build a temporary database path.
    db_path = tmp_path / "water.db"
    # Build a temporary log path.
    log_path = tmp_path / "system_logs.log"
    # Redirect the database path into the temp folder.
    monkeypatch.setenv("WATER_DB_PATH", str(db_path))
    # Redirect the log path into the temp folder.
    monkeypatch.setenv("WATER_LOG_PATH", str(log_path))

    # List the modules that cache runtime state.
    modules_to_clear = [
        "main",
        "database",
        "logger_config",
        "sensor_simulator",
        "leak_detector",
        "analytics",
        "routes.telemetry",
        "routes.alerts",
        "routes.analytics_routes",
        "routes.infrastructure",
    ]
    # Remove each cached module before the test runs.
    for module_name in modules_to_clear:
        sys.modules.pop(module_name, None)

    # Expose the temp paths to the test.
    yield {
        "db_path": db_path,
        "log_path": log_path,
    }


# Provide a TestClient connected to the FastAPI app.
@pytest.fixture()
def app_client(isolated_environment):
    # Import the main application after environment setup.
    import main
    # Import TestClient from FastAPI.
    from fastapi.testclient import TestClient

    # Create a client for the app.
    with TestClient(main.app) as client:
        # Yield the client to the test.
        yield client
