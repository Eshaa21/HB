# This file calculates water system analytics and summary statistics
# It reads water data from the database and creates reports
# Reports show average water flow, pressure, consumption, and leak counts
# Reports are broken down by area and pipeline

# Import to use decorators and type hints
from __future__ import annotations

# Import SQLite library to access database
import sqlite3

# Import Pandas library to analyze data easily
# Pandas makes it easy to group data and calculate averages
import pandas as pd

# Import database functions
from database import get_connection, initialize_database, normalize_area_name  # functions to access database
# Import logging functions to write messages
from logger_config import get_logger

# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# Helper function to read SQL query results into a data table
def _load_dataframe(connection: sqlite3.Connection, query: str) -> pd.DataFrame:
    """Load a SQL query result into a Pandas DataFrame (data table)
    
    This is called by: generate_analytics_summary function in this file
    
    What this does:
        1. Run a SELECT query on the database
        2. Convert results into a Pandas DataFrame (like an Excel table)
        3. Return the table for analysis
    
    Args:
        connection: Open SQLite database connection
        query: SQL SELECT query to run (like "SELECT * FROM telemetry")

    Returns:
        Pandas DataFrame (data table) containing the query results
    """
    # Read SQL query results into a Pandas DataFrame (data table)
    return pd.read_sql_query(query, connection)


# Calculate water flow, consumption, loss, and leak analytics
def generate_analytics_summary() -> dict[str, object]:
    """Calculate water-flow, consumption, loss, and leak analytics from database
    
    This is called by: get_analytics function in routes/analytics_routes.py
    
    What this function does:
        1. Read all water readings from telemetry table
        2. Read all leak alerts from alerts table
        3. Read all areas and pipelines
        4. Calculate total water flow and consumption
        5. Calculate water loss (flow - consumption)
        6. Calculate average pressure
        7. Calculate leak count
        8. Group all data by area
        9. Group all data by pipeline within each area
        10. Return detailed summary with all breakdowns
    
    Returns:
        Dictionary with water analytics:
        {
            "total_water_flow": 1000.50,  # total water flowing across all areas
            "total_consumption": 950.25,  # total water used across all areas
            "water_loss": 50.25,  # water lost (flow - consumption)
            "average_pressure": 55.5,  # average pressure across all areas
            "leak_count": 5,  # total number of leaks detected
            "area_wise_statistics": [  # breakdown by area
                {
                    "area_name": "Kothrud",
                    "average_flow": 500.25,
                    "average_pressure": 55.0,
                    "average_consumption": 475.12,
                    "leak_count": 2,
                    "pipelines": [  # breakdown by pipeline within area
                        {
                            "pipeline_name": "KOTH_P1",
                            "average_flow": 250.0,
                            "average_pressure": 55.5,
                            "average_consumption": 235.0,
                            "leak_count": 1
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    # Initialize database (create tables if they don't exist)
    initialize_database()

    # Open database connection and read data
    with get_connection() as connection:
        # Read all water readings from telemetry table into a data table
        telemetry_df = _load_dataframe(connection, "SELECT * FROM telemetry")
        # Read all leak alerts from alerts table into a data table
        alerts_df = _load_dataframe(connection, "SELECT * FROM alerts")
        # Read all registered areas from areas table into a data table
        areas_df = _load_dataframe(connection, "SELECT area_name FROM areas")
        # Read all registered pipelines from pipelines table into a data table
        pipelines_df = _load_dataframe(connection, "SELECT area_name, pipeline_name FROM pipelines")

    # Standardize all area names in the data tables (like "kothrud" becomes "Kothrud")
    if not telemetry_df.empty:
        # Apply normalize_area_name function to all area names in telemetry data
        telemetry_df["area_name"] = telemetry_df["area_name"].map(normalize_area_name)
    # Standardize area names in alerts data
    if not alerts_df.empty:
        alerts_df["area_name"] = alerts_df["area_name"].map(normalize_area_name)
    # Standardize area names in areas data
    if not areas_df.empty:
        areas_df["area_name"] = areas_df["area_name"].map(normalize_area_name)
    # Standardize area names in pipelines data
    if not pipelines_df.empty:
        pipelines_df["area_name"] = pipelines_df["area_name"].map(normalize_area_name)

    # Check if we have any water readings in the database
    if telemetry_df.empty:
        # If no water readings, set all values to zero
        total_water_flow = 0.0  # no water flow data
        total_consumption = 0.0  # no consumption data
        water_loss = 0.0  # no loss data
        average_pressure = 0.0  # no pressure data
        # Create empty tables for area and pipeline summaries
        telemetry_area_summary = pd.DataFrame(
            columns=["area_name", "average_flow", "average_pressure", "average_consumption"]
        )
        telemetry_pipeline_summary = pd.DataFrame(
            columns=["area_name", "pipeline_name", "average_flow", "average_pressure", "average_consumption"]
        )
    else:
        # Calculate total water flow by adding all flow_rate values
        total_water_flow = float(telemetry_df["flow_rate"].sum())
        # Calculate total water consumption by adding all consumption values
        total_consumption = float(telemetry_df["consumption"].sum())
        # Calculate water loss by subtracting consumption from flow
        # Example: if flow is 1000 and consumption is 950, loss is 50
        water_loss = float((telemetry_df["flow_rate"] - telemetry_df["consumption"]).sum())
        # Calculate average pressure across all readings
        average_pressure = float(telemetry_df["pressure"].mean())

        # Group water readings by area and calculate averages
        telemetry_area_summary = (
            # Group all readings by area_name
            telemetry_df.groupby("area_name", as_index=False)
            # Calculate average flow, pressure, and consumption for each area
            .agg(
                average_flow=("flow_rate", "mean"),  # average water flow
                average_pressure=("pressure", "mean"),  # average pressure
                average_consumption=("consumption", "mean"),  # average consumption
            )
        )
        # Group water readings by area AND pipeline and calculate averages
        telemetry_pipeline_summary = (
            # Group all readings by area and pipeline
            telemetry_df.groupby(["area_name", "pipeline_name"], as_index=False)
            # Calculate average flow, pressure, and consumption for each pipeline
            .agg(
                average_flow=("flow_rate", "mean"),  # average water flow
                average_pressure=("pressure", "mean"),  # average pressure
                average_consumption=("consumption", "mean"),  # average consumption
            )
        )

    # Count the total number of leaks detected
    leak_count = int(len(alerts_df))
    # Check if we have any leaks in the database
    if alerts_df.empty:
        # If no leaks, create empty tables for area and pipeline leak summaries
        alert_area_summary = pd.DataFrame(columns=["area_name", "leak_count"])
        alert_pipeline_summary = pd.DataFrame(columns=["area_name", "pipeline_name", "leak_count"])
    else:
        # Group leaks by area and count how many leaks in each area
        alert_area_summary = alerts_df.groupby("area_name", as_index=False).size().rename(columns={"size": "leak_count"})
        # Group leaks by area AND pipeline and count how many leaks in each pipeline
        alert_pipeline_summary = (
            alerts_df.groupby(["area_name", "pipeline_name"], as_index=False)
            .size()
            .rename(columns={"size": "leak_count"})
        )

    # Combine area statistics with leak data
    # Start with all areas and join telemetry data, then join alert data
    area_summary = areas_df.merge(telemetry_area_summary, on="area_name", how="left").merge(
        alert_area_summary,
        on="area_name",
        how="left",
    )
    # Replace empty values with zeros (areas with no data)
    area_summary = area_summary.fillna(
        {
            "average_flow": 0.0,  # no flow = 0
            "average_pressure": 0.0,  # no pressure = 0
            "average_consumption": 0.0,  # no consumption = 0
            "leak_count": 0,  # no leaks = 0
        }
    )

    # Combine pipeline statistics with leak data
    # Start with all pipelines and join telemetry data, then join alert data
    pipeline_summary = pipelines_df.merge(
        telemetry_pipeline_summary,
        on=["area_name", "pipeline_name"],
        how="left",
    ).merge(
        alert_pipeline_summary,
        on=["area_name", "pipeline_name"],
        how="left",
    )
    # Replace empty values with zeros (pipelines with no data)
    pipeline_summary = pipeline_summary.fillna(
        {
            "average_flow": 0.0,  # no flow = 0
            "average_pressure": 0.0,  # no pressure = 0
            "average_consumption": 0.0,  # no consumption = 0
            "leak_count": 0,  # no leaks = 0
        }
    )

    # Build the final area statistics list with nested pipeline info
    area_statistics = []
    # Go through each area in the area summary
    for _, area_row in area_summary.iterrows():
        # Find all pipelines that belong to this area
        matching_pipelines = pipeline_summary[pipeline_summary["area_name"] == area_row["area_name"]]
        # Create an area entry with all its information
        area_statistics.append(
            {
                "area_name": area_row["area_name"],  # name of the area
                "average_flow": round(float(area_row["average_flow"]), 2),  # average flow rounded to 2 decimals
                "average_pressure": round(float(area_row["average_pressure"]), 2),  # average pressure rounded to 2 decimals
                "average_consumption": round(float(area_row["average_consumption"]), 2),  # average consumption rounded to 2 decimals
                "leak_count": int(area_row["leak_count"]),  # number of leaks in this area
                # Create list of pipelines within this area
                "pipelines": [
                    {
                        "pipeline_name": pipeline_row["pipeline_name"],  # name of the pipeline
                        "average_flow": round(float(pipeline_row["average_flow"]), 2),  # average flow rounded
                        "average_pressure": round(float(pipeline_row["average_pressure"]), 2),  # average pressure rounded
                        "average_consumption": round(float(pipeline_row["average_consumption"]), 2),  # average consumption rounded
                        "leak_count": int(pipeline_row["leak_count"]),  # number of leaks in this pipeline
                    }
                    # Go through each pipeline and create entry for each one
                    for _, pipeline_row in matching_pipelines.iterrows()
                ],
            }
        )

    # Write a log message saying analytics were calculated
    logger.info("Analytics requested")
    # Return the complete analytics summary
    return {
        "total_water_flow": round(total_water_flow, 2),  # total flow across all areas rounded to 2 decimals
        "total_consumption": round(total_consumption, 2),  # total consumption across all areas rounded to 2 decimals
        "water_loss": round(water_loss, 2),  # total water loss rounded to 2 decimals
        "average_pressure": round(average_pressure, 2),  # average pressure rounded to 2 decimals
        "leak_count": leak_count,  # total number of leaks
        "area_wise_statistics": area_statistics,  # list of all areas with their stats
    }


# This is an old name kept for backward compatibility with older code
def generate_analytics_summary_from_records() -> dict[str, object]:
    """Backward-compatible alias used by older imports/tests
    
    This function is called for backward compatibility only
    It just calls generate_analytics_summary with the same name as before
    """
    # Call the main analytics function
    return generate_analytics_summary()
