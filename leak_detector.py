# This file checks water sensor readings to detect if there is a leak
# It uses three rules to decide if water readings show a problem

# Import to use decorators and type hints
from __future__ import annotations

# Import to get current date and time for alert timestamps
from datetime import datetime, timezone

# Import logging to write messages about leak detection
from logger_config import get_logger

# Create a logger object to write log messages for this file
logger = get_logger(__name__)


# Check water readings against three leak detection rules
def evaluate_leak_rules(
    flow_rate: float,  # how much water is flowing
    pressure: float,  # water pressure in pipes
    consumption: float,  # how much water is being used
    previous_pressure: float | None = None,  # last pressure reading from previous check
) -> list[dict[str, str]]:
    """Evaluate the three case-study leak detection rules
    
    This is called by: detect_leak function in this file
    
    The three rules are:
    
    Rule 1: Check if pressure is too low
        - If pressure drops below 40 PSI, there might be a leak
        - Low pressure means water is escaping somewhere
        - Severity: CRITICAL (very bad)
    
    Rule 2: Check if flow rate is much higher than consumption
        - If water flowing is much more than water being used, water is lost somewhere
        - If flow_rate > consumption + 30, there is a leak
        - Severity: WARNING (not as bad as critical)
    
    Rule 3: Check if pressure suddenly dropped
        - If pressure dropped more than 20% compared to last reading, something broke
        - This detects burst pipes
        - Severity: CRITICAL (very bad)

    Args:
        flow_rate: Current water flow reading (like 125.45)
        pressure: Current water pressure reading (like 55.67)
        consumption: Current water usage reading (like 95.23)
        previous_pressure: Pressure from the last reading (used to detect sudden drops)

    Returns:
        List of triggered (fired) leak rules. Empty list means no leak detected.
        Example: [{"rule": "Rule 1", "message": "...", "severity": "CRITICAL"}]
    """
    # Create empty list to store rules that triggered
    triggered_rules: list[dict[str, str]] = []

    # RULE 1: Check if pressure is below 40 PSI (too low)
    if pressure < 40:
        # Write a warning message to logs
        logger.warning("Pressure dropped below 40 PSI")
        # Add Rule 1 to triggered rules list
        triggered_rules.append(
            {
                "rule": "Rule 1",  # name of the rule
                "message": "Pressure dropped below 40 PSI",  # what happened
                "severity": "CRITICAL",  # how serious this is
            }
        )

    # RULE 2: Check if flow is much higher than consumption
    if flow_rate > consumption + 30:
        # Write a warning message to logs
        logger.warning("Flow rate is much higher than consumption")
        # Add Rule 2 to triggered rules list
        triggered_rules.append(
            {
                "rule": "Rule 2",  # name of the rule
                "message": "Flow rate is more than consumption by 30 L/Day",  # what happened
                "severity": "WARNING",  # how serious this is
            }
        )

    # RULE 3: Check if pressure suddenly dropped compared to last reading
    # Only check this rule if we have a previous pressure reading to compare
    if previous_pressure is not None and previous_pressure > 0:
        # Calculate what percent the pressure dropped
        # Example: if pressure was 100 and now 80, drop is 20%
        pressure_drop = ((previous_pressure - pressure) / previous_pressure) * 100
        # If pressure dropped more than 20%
        if pressure_drop > 20:
            # Write a warning message to logs
            logger.warning("Sudden pressure drop detected")
            # Add Rule 3 to triggered rules list
            triggered_rules.append(
                {
                    "rule": "Rule 3",  # name of the rule
                    "message": f"Sudden pressure drop greater than 20% ({pressure_drop:.2f}%)",  # what happened with the percent
                    "severity": "CRITICAL",  # how serious this is
                }
            )

    # Return all the rules that triggered (or empty list if no rules triggered)
    return triggered_rules


# Create an alert record to save to database
def build_alert_record(
    area_name: str,  # which area has the leak
    pipeline_name: str,  # which pipeline has the leak
    triggered_rules: list[dict[str, str]],  # the rules that detected the leak
) -> dict[str, str]:
    """Build the alert row to save to SQLite database
    
    This is called by: detect_leak function in this file
    
    What this does:
        1. Check if any rule is CRITICAL severity (very bad)
        2. If yes, set alert severity to CRITICAL
        3. If no, set alert severity to WARNING
        4. Combine all triggered rule messages into one long message
        5. Create alert dictionary with area, pipeline, type, severity, message, timestamp

    Args:
        area_name: Area where the leak was detected (like "Kothrud")
        pipeline_name: Pipeline where the leak was detected (like "KOTH_P1")
        triggered_rules: List of rules that detected the leak
                        Example: [{"rule": "Rule 1", "message": "...", "severity": "CRITICAL"}]

    Returns:
        Alert dictionary ready to save to database:
        {
            "area_name": "Kothrud",
            "pipeline_name": "KOTH_P1",
            "alert_type": "Leak Detected",
            "severity": "CRITICAL",
            "message": "Pressure dropped below 40 PSI; Flow rate is more than consumption by 30 L/Day",
            "timestamp": "2026-06-06T12:30:00+00:00"
        }
    """
    # Start with severity as WARNING
    severity = "WARNING"
    # Check if any of the triggered rules are CRITICAL
    # If yes, upgrade severity to CRITICAL
    if any(rule["severity"] == "CRITICAL" for rule in triggered_rules):
        # Change severity to CRITICAL (more serious than WARNING)
        severity = "CRITICAL"

    # Create and return the alert dictionary
    return {
        "area_name": area_name,  # which area
        "pipeline_name": pipeline_name,  # which pipeline
        "alert_type": "Leak Detected",  # type of alert
        "severity": severity,  # how serious (CRITICAL or WARNING)
        # Combine all rule messages with semicolon between them
        # Example: "Rule 1 message; Rule 2 message"
        "message": "; ".join(rule["message"] for rule in triggered_rules),
        # Get current date and time
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Check if a water reading indicates a leak
def detect_leak(
    record: dict[str, object],  # the water reading to check
    previous_pressure: float | None = None,  # the last pressure reading
) -> dict[str, str] | None:
    """Detect whether a telemetry record should create a leak alert
    
    This is called by: generate_sensor_record in sensor_simulator.py
    
    What this function does:
        1. Evaluate the reading against the three leak rules
        2. If any rule triggered, build and return an alert
        3. If no rules triggered, return None (no leak)

    Args:
        record: Water reading dictionary containing:
                - area_name: which area
                - pipeline_name: which pipeline
                - flow_rate: water flow value
                - pressure: water pressure value
                - consumption: water usage value
        previous_pressure: Pressure from the last reading (for detecting sudden drops)

    Returns:
        Alert dictionary if a leak was detected, or None if no leak
        Example return (if leak detected):
        {
            "area_name": "Kothrud",
            "pipeline_name": "KOTH_P1",
            "alert_type": "Leak Detected",
            "severity": "CRITICAL",
            "message": "...",
            "timestamp": "..."
        }
        
        Example return (if no leak): None
    """
    # Check the reading against all three leak rules
    triggered_rules = evaluate_leak_rules(
        flow_rate=float(record["flow_rate"]),  # convert to float and pass
        pressure=float(record["pressure"]),  # convert to float and pass
        consumption=float(record["consumption"]),  # convert to float and pass
        previous_pressure=previous_pressure,  # pass the previous pressure
    )

    # If no rules triggered, no leak detected
    if not triggered_rules:
        # Return None to indicate no leak
        return None

    # If at least one rule triggered, build an alert and return it
    alert = build_alert_record(
        area_name=str(record["area_name"]),  # convert to string
        pipeline_name=str(record["pipeline_name"]),  # convert to string
        triggered_rules=triggered_rules,  # the rules that triggered
    )
    # Write a critical warning message to logs about the leak detection
    logger.critical("Leak detected in %s/%s", record["area_name"], record["pipeline_name"])
    # Return the alert dictionary
    return alert
