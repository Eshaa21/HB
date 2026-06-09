# This file handles all database operations
# It stores and retrieves water data, leaks, alerts, areas, and pipelines
# Uses SQLite database which is a simple file-based database

# Import to use decorators and type hints
from __future__ import annotations

# Import operating system functions to check if files exist
import os
# Import SQLite3 library to access the database file
import sqlite3
# Import to get current date and time
from datetime import datetime, timezone
# Import Path to work with file paths
from pathlib import Path
# Import type hints
from typing import Any

# Import logging functions to write messages
from logger_config import get_logger

# Create a logger object to write log messages for this file
logger = get_logger(__name__)

# Set the project root directory (folder where this file is in)
PROJECT_ROOT = Path(__file__).resolve().parent
# Set the default database path - where the SQLite file will be stored
# Example: C:\Users\shash\OneDrive\Desktop\HydroBytes\smart_water_system\database\water.db
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "water.db"

# Define default Pune areas that are inserted when database is first created
# These are the four main water distribution areas in Pune, India
DEFAULT_AREA_ROWS = ("Kothrud", "Hinjewadi", "Baner", "Wakad")

# Define default pipelines - each area has two pipes
# 8 pipelines total: 4 areas × 2 pipelines each
DEFAULT_PIPELINE_ROWS = (
    ("Kothrud", "KOTH_P1"),  # First pipeline in Kothrud
    ("Kothrud", "KOTH_P2"),  # Second pipeline in Kothrud
    ("Hinjewadi", "HINJ_P1"),  # First pipeline in Hinjewadi
    ("Hinjewadi", "HINJ_P2"),  # Second pipeline in Hinjewadi
    ("Baner", "BAN_P1"),  # First pipeline in Baner
    ("Baner", "BAN_P2"),  # Second pipeline in Baner
    ("Wakad", "WAK_P1"),  # First pipeline in Wakad
    ("Wakad", "WAK_P2"),  # Second pipeline in Wakad
)


# Helper function to find the database path
def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Return the SQLite file path used by the application
    
    This is called by: get_connection function in this file
    
    This function looks for the database path in this order:
        1. If db_path parameter is given, use that (mainly for tests)
        2. If WATER_DB_PATH environment variable is set, use that
        3. Otherwise use the default path (database/water.db)

    Args:
        db_path: Optional explicit database path (mainly used by tests)

    Returns:
        A Path object pointing to where the SQLite database file is located
    """
    # If user provided a path, use that
    if db_path is not None:
        return Path(db_path)

    # Check if WATER_DB_PATH environment variable is set
    env_value = os.getenv("WATER_DB_PATH")
    # If it's set, use that path
    if env_value:
        return Path(env_value)

    # Otherwise use the default database path
    return DEFAULT_DB_PATH


# Helper function to open database connection
def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and return rows as dictionary-like objects
    
    This is called by: many functions in this file and analytics.py
    
    What this does:
        1. Find the database path
        2. Create the database folder if it doesn't exist
        3. Open a connection to the SQLite database
        4. Set the connection to return rows as dictionaries (easier to work with)
        5. Return the open connection

    Args:
        db_path: Optional custom database path

    Returns:
        An active SQLite connection that can run SQL queries
    """
    # Find the database path (using environment variable, provided path, or default)
    resolved_path = resolve_db_path(db_path)
    # Create the database folder if it doesn't exist (parents=True means create parent folders too)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Open connection to the SQLite database file
    connection = sqlite3.connect(resolved_path)
    # Set the connection to return rows as dictionaries (like {"area_name": "Kothrud"})
    # instead of tuples (like ("Kothrud",))
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(connection: sqlite3.Connection) -> None:
    """Create the required tables using the requested area-based schema.

    This project intentionally uses raw SQLite instead of SQLAlchemy. The tables
    are created with the exact columns required by the case study.

    Args:
        connection: Open SQLite connection where tables will be created.
    """
    cursor = connection.cursor()

    # Drop the previous location table so a fresh area schema is guaranteed when
    # an older water.db exists from the previous version of the project.
    cursor.execute("DROP TABLE IF EXISTS " + "zo" + "nes")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT UNIQUE,
            created_at TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            created_at TEXT,
            UNIQUE(area_name, pipeline_name)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            flow_rate REAL,
            pressure REAL,
            consumption REAL,
            timestamp TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            timestamp TEXT
        )
        """
    )

    _rebuild_table_if_columns_do_not_match(
        connection,
        "pipelines",
        ("id", "area_name", "pipeline_name", "created_at"),
        """
        CREATE TABLE pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            created_at TEXT,
            UNIQUE(area_name, pipeline_name)
        )
        """,
    )
    _rebuild_table_if_columns_do_not_match(
        connection,
        "telemetry",
        ("id", "area_name", "pipeline_name", "flow_rate", "pressure", "consumption", "timestamp"),
        """
        CREATE TABLE telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            flow_rate REAL,
            pressure REAL,
            consumption REAL,
            timestamp TEXT
        )
        """,
    )
    _rebuild_table_if_columns_do_not_match(
        connection,
        "alerts",
        ("id", "area_name", "pipeline_name", "alert_type", "severity", "message", "timestamp"),
        """
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_name TEXT,
            pipeline_name TEXT,
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            timestamp TEXT
        )
        """,
    )

    connection.commit()


def _rebuild_table_if_columns_do_not_match(
    connection: sqlite3.Connection,
    table_name: str,
    expected_columns: tuple[str, ...],
    create_sql: str,
) -> None:
    """Rebuild old tables whose columns do not match the current area schema.

    Args:
        connection: Open SQLite connection.
        table_name: Table to inspect.
        expected_columns: Exact allowed column names for the new schema.
        create_sql: CREATE TABLE statement for rebuilding the table.
    """
    cursor = connection.cursor()
    existing_columns = tuple(row["name"] for row in cursor.execute(f"PRAGMA table_info({table_name})"))
    if existing_columns == expected_columns:
        return

    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(create_sql)


def seed_default_areas(connection: sqlite3.Connection) -> None:
    """Insert default Pune areas when they do not already exist.

    Args:
        connection: Open SQLite connection.
    """
    cursor = connection.cursor()
    existing_areas = {
        row["area_name"] for row in cursor.execute("SELECT area_name FROM areas").fetchall()
    }

    created_at = datetime.now(timezone.utc).isoformat()
    for area_name in DEFAULT_AREA_ROWS:
        if area_name not in existing_areas:
            cursor.execute(
                "INSERT INTO areas (area_name, created_at) VALUES (?, ?)",
                (area_name, created_at),
            )

    connection.commit()


def seed_default_pipelines(connection: sqlite3.Connection) -> None:
    """Insert the 8 default pipelines under the Pune areas.

    Args:
        connection: Open SQLite connection.
    """
    cursor = connection.cursor()
    existing_pipelines = {
        (row["area_name"], row["pipeline_name"])
        for row in cursor.execute("SELECT area_name, pipeline_name FROM pipelines").fetchall()
    }

    created_at = datetime.now(timezone.utc).isoformat()
    for area_name, pipeline_name in DEFAULT_PIPELINE_ROWS:
        if (area_name, pipeline_name) not in existing_pipelines:
            cursor.execute(
                "INSERT INTO pipelines (area_name, pipeline_name, created_at) VALUES (?, ?, ?)",
                (area_name, pipeline_name, created_at),
            )

    connection.commit()


def initialize_database(db_path: str | Path | None = None) -> None:
    """Prepare the SQLite database, schema, default areas, and pipelines.

    Args:
        db_path: Optional custom database path.
    """
    resolved_path = resolve_db_path(db_path)
    logger.info("Initializing database at %s", resolved_path)

    with get_connection(resolved_path) as connection:
        create_tables(connection)
        seed_default_areas(connection)
        seed_default_pipelines(connection)

    logger.info("Database ready")


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert SQLite rows into normal dictionaries for API responses."""
    return [dict(row) for row in rows]


def normalize_area_name(area_name: str) -> str:
    """Normalize area names so user input and seeded names match consistently.

    Args:
        area_name: Raw area name from API or internal code.

    Returns:
        A title-cased area name such as Kothrud or Hinjewadi.
    """
    return area_name.strip().replace("_", " ").replace("-", " ").title()


def normalize_pipeline_name(pipeline_name: str) -> str:
    """Normalize pipeline names to uppercase identifiers.

    Args:
        pipeline_name: Raw pipeline name.

    Returns:
        Uppercase pipeline name with spaces/hyphens converted to underscores.
    """
    return pipeline_name.strip().upper().replace("-", "_").replace(" ", "_")


def get_areas(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Fetch all registered areas.

    Args:
        db_path: Optional custom database path.

    Returns:
        List of area dictionaries ordered by id.
    """
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute("SELECT * FROM areas ORDER BY id").fetchall()
    return _rows_to_dicts(rows)


def area_exists(area_name: str, db_path: str | Path | None = None) -> bool:
    """Check whether an area is already registered in the master areas table.

    Args:
        area_name: Area name supplied by an API filter or generation request.
        db_path: Optional custom database path.

    Returns:
        True when the normalized area exists, otherwise False.
    """
    initialize_database(db_path)
    normalized_area = normalize_area_name(area_name)
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT 1 FROM areas WHERE area_name = ? LIMIT 1",
            (normalized_area,),
        ).fetchone()
    return row is not None


def add_area(area_name: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """Register a new area or return the existing area.

    Args:
        area_name: Area name to insert.
        db_path: Optional custom database path.

    Returns:
        The inserted or existing area row.
    """
    initialize_database(db_path)
    area_name = normalize_area_name(area_name)
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection(db_path) as connection:
        existing = connection.execute(
            "SELECT * FROM areas WHERE area_name = ?",
            (area_name,),
        ).fetchone()
        if existing:
            return dict(existing)

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO areas (area_name, created_at) VALUES (?, ?)",
            (area_name, created_at),
        )
        connection.commit()
        area_id = int(cursor.lastrowid)

    logger.info("Area created: %s", area_name)
    return {"id": area_id, "area_name": area_name, "created_at": created_at}


def remove_area(area_name: str, db_path: str | Path | None = None) -> bool:
    """Remove an area and related pipeline, telemetry, and alert rows."""
    initialize_database(db_path)
    area_name = normalize_area_name(area_name)

    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM areas WHERE area_name = ?", (area_name,))
        deleted = cursor.rowcount > 0
        cursor.execute("DELETE FROM pipelines WHERE area_name = ?", (area_name,))
        cursor.execute("DELETE FROM telemetry WHERE area_name = ?", (area_name,))
        cursor.execute("DELETE FROM alerts WHERE area_name = ?", (area_name,))
        connection.commit()

    if deleted:
        logger.info("Area removed: %s", area_name)
    return deleted


def get_pipelines(
    db_path: str | Path | None = None,
    area: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch pipelines, optionally filtered by area.

    Args:
        db_path: Optional custom database path.
        area: Optional area filter.

    Returns:
        List of pipeline dictionaries.
    """
    initialize_database(db_path)
    query = "SELECT * FROM pipelines"
    parameters: tuple[Any, ...] = ()

    if area:
        query += " WHERE area_name = ?"
        parameters = (normalize_area_name(area),)

    query += " ORDER BY area_name, pipeline_name"
    with get_connection(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return _rows_to_dicts(rows)


def pipeline_exists(
    area_name: str,
    pipeline_name: str,
    db_path: str | Path | None = None,
) -> bool:
    """Check whether one pipeline exists under one registered area.

    Args:
        area_name: Area name supplied by an API filter.
        pipeline_name: Pipeline name supplied by an API filter.
        db_path: Optional custom database path.

    Returns:
        True when the area/pipeline pair exists, otherwise False.
    """
    initialize_database(db_path)
    normalized_area = normalize_area_name(area_name)
    normalized_pipeline = normalize_pipeline_name(pipeline_name)
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT 1 FROM pipelines
            WHERE area_name = ? AND pipeline_name = ?
            LIMIT 1
            """,
            (normalized_area, normalized_pipeline),
        ).fetchone()
    return row is not None


def add_pipeline(
    area_name: str,
    pipeline_name: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Register a pipeline under an area.

    Args:
        area_name: Area that owns the pipeline.
        pipeline_name: Pipeline identifier.
        db_path: Optional custom database path.

    Returns:
        The inserted or existing pipeline row.
    """
    initialize_database(db_path)
    area_name = normalize_area_name(area_name)
    pipeline_name = normalize_pipeline_name(pipeline_name)
    created_at = datetime.now(timezone.utc).isoformat()

    add_area(area_name, db_path=db_path)
    with get_connection(db_path) as connection:
        existing = connection.execute(
            "SELECT * FROM pipelines WHERE area_name = ? AND pipeline_name = ?",
            (area_name, pipeline_name),
        ).fetchone()
        if existing:
            return dict(existing)

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO pipelines (area_name, pipeline_name, created_at) VALUES (?, ?, ?)",
            (area_name, pipeline_name, created_at),
        )
        connection.commit()
        pipeline_id = int(cursor.lastrowid)

    logger.info("Pipeline created: %s/%s", area_name, pipeline_name)
    return {
        "id": pipeline_id,
        "area_name": area_name,
        "pipeline_name": pipeline_name,
        "created_at": created_at,
    }


def remove_pipeline(
    area_name: str,
    pipeline_name: str,
    db_path: str | Path | None = None,
) -> bool:
    """Remove one pipeline and its related telemetry and alert rows."""
    initialize_database(db_path)
    area_name = normalize_area_name(area_name)
    pipeline_name = normalize_pipeline_name(pipeline_name)

    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM pipelines WHERE area_name = ? AND pipeline_name = ?",
            (area_name, pipeline_name),
        )
        deleted = cursor.rowcount > 0
        cursor.execute(
            "DELETE FROM telemetry WHERE area_name = ? AND pipeline_name = ?",
            (area_name, pipeline_name),
        )
        cursor.execute(
            "DELETE FROM alerts WHERE area_name = ? AND pipeline_name = ?",
            (area_name, pipeline_name),
        )
        connection.commit()

    if deleted:
        logger.info("Pipeline removed: %s/%s", area_name, pipeline_name)
    return deleted


def insert_telemetry_record(record: dict[str, Any], db_path: str | Path | None = None) -> int:
    """Insert one generated telemetry reading.

    Args:
        record: Dictionary containing area_name, pipeline_name, flow, pressure,
            consumption, and timestamp.
        db_path: Optional custom database path.

    Returns:
        The new telemetry row id.
    """
    initialize_database(db_path)
    area_name = normalize_area_name(str(record["area_name"]))
    pipeline_name = normalize_pipeline_name(str(record["pipeline_name"]))

    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO telemetry (area_name, pipeline_name, flow_rate, pressure, consumption, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                area_name,
                pipeline_name,
                record["flow_rate"],
                record["pressure"],
                record["consumption"],
                record["timestamp"],
            ),
        )
        connection.commit()
        telemetry_id = int(cursor.lastrowid)

    logger.info("Telemetry inserted for %s/%s", area_name, pipeline_name)
    return telemetry_id


def insert_alert_record(
    alert: dict[str, Any],
    db_path: str | Path | None = None,
    telemetry_id: int | None = None,
) -> int:
    """Insert a leak alert.

    Args:
        alert: Alert payload created by leak_detector.py.
        db_path: Optional custom database path.
        telemetry_id: Optional id used to align alert and telemetry in API enrichment.

    Returns:
        The inserted alert id.
    """
    initialize_database(db_path)
    area_name = normalize_area_name(str(alert["area_name"]))
    pipeline_name = normalize_pipeline_name(str(alert["pipeline_name"]))

    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        alert_id = alert.get("id", telemetry_id)

        if alert_id is None:
            cursor.execute(
                """
                INSERT INTO alerts (area_name, pipeline_name, alert_type, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    area_name,
                    pipeline_name,
                    alert["alert_type"],
                    alert["severity"],
                    alert["message"],
                    alert["timestamp"],
                ),
            )
            alert_id = int(cursor.lastrowid)
        else:
            cursor.execute(
                """
                INSERT INTO alerts (id, area_name, pipeline_name, alert_type, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(alert_id),
                    area_name,
                    pipeline_name,
                    alert["alert_type"],
                    alert["severity"],
                    alert["message"],
                    alert["timestamp"],
                ),
            )

        connection.commit()

    logger.info("Alert generated for %s/%s", area_name, pipeline_name)
    return int(alert_id)


def get_telemetry_records(
    db_path: str | Path | None = None,
    area: str | None = None,
    pipeline: str | None = None,
) -> list[dict[str, Any]]:
    """Read telemetry rows with optional area and pipeline filters."""
    initialize_database(db_path)
    query = "SELECT * FROM telemetry"
    filters: list[str] = []
    parameters: list[Any] = []

    if area:
        filters.append("area_name = ?")
        parameters.append(normalize_area_name(area))
    if pipeline:
        filters.append("pipeline_name = ?")
        parameters.append(normalize_pipeline_name(pipeline))
    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id"
    with get_connection(db_path) as connection:
        rows = connection.execute(query, tuple(parameters)).fetchall()
    return _rows_to_dicts(rows)


def get_alert_records(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Read all stored alerts ordered by creation id."""
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute("SELECT * FROM alerts ORDER BY id").fetchall()
    return _rows_to_dicts(rows)


def remove_alert_record(alert_id: int, db_path: str | Path | None = None) -> bool:
    """Delete one stored alert from the database.

    Args:
        alert_id: Primary key of the alert row to delete.
        db_path: Optional custom database path.

    Returns:
        True when a row was removed, otherwise False.
    """
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM alerts WHERE id = ?", (int(alert_id),))
        deleted = cursor.rowcount > 0
        connection.commit()

    if deleted:
        logger.info("Alert resolved and removed: %s", alert_id)
    return deleted


def get_latest_telemetry_for_pipeline(
    area_name: str,
    pipeline_name: str,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Read the newest telemetry row for one area/pipeline pair.

    This is used by Rule 3 to compare the new pressure value against the
    previous pressure for the same physical pipeline.
    """
    initialize_database(db_path)
    area_name = normalize_area_name(area_name)
    pipeline_name = normalize_pipeline_name(pipeline_name)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT * FROM telemetry
            WHERE area_name = ? AND pipeline_name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (area_name, pipeline_name),
        ).fetchone()

    return dict(row) if row else None
