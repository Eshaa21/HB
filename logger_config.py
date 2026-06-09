from __future__ import annotations

# Import the logging module.
import logging
# Import environment variable access.
import os
# Import Path for filesystem paths.
from pathlib import Path

# Define the shared logger name.
LOGGER_NAME = "smart_water_system"
# Track the current configured log file.
_configured_log_file: Path | None = None


# Resolve the log file path from the environment or default location.
def get_log_file_path() -> Path:
    # Read the optional custom log path.
    env_value = os.getenv("WATER_LOG_PATH")
    # Use the custom path if it was provided.
    if env_value:
        return Path(env_value)
    # Fall back to the project logs folder.
    return Path(__file__).resolve().parent / "logs" / "system_logs.log"


# Configure file and console logging.
def setup_logging() -> logging.Logger:
    # Access the module-level cached path.
    global _configured_log_file

    # Get the shared logger instance.
    logger = logging.getLogger(LOGGER_NAME)
    # Resolve the target log file.
    log_file = get_log_file_path()

    # Reuse existing handlers if this file is already configured.
    if _configured_log_file == log_file and logger.handlers:
        return logger

    # Remove any previous handlers before reconfiguring.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    # Ensure the log folder exists.
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # Ensure the log file exists.
    log_file.touch(exist_ok=True)

    # Set the logging level.
    logger.setLevel(logging.INFO)
    # Prevent duplicate propagation to the root logger.
    logger.propagate = False

    # Use a readable audit-trail format.
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")

    # Create the file handler.
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    # Apply the formatter to the file handler.
    file_handler.setFormatter(formatter)

    # Create the console handler.
    stream_handler = logging.StreamHandler()
    # Apply the same formatter to the console handler.
    stream_handler.setFormatter(formatter)

    # Attach the file handler.
    logger.addHandler(file_handler)
    # Attach the console handler.
    logger.addHandler(stream_handler)

    # Cache the active log file path.
    _configured_log_file = log_file
    # Return the configured logger.
    return logger


# Get a named logger under the project namespace.
def get_logger(name: str | None = None) -> logging.Logger:
    # Ensure logging is configured first.
    setup_logging()
    # Return the requested child logger if a name was supplied.
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    # Otherwise return the project logger.
    return logging.getLogger(LOGGER_NAME)


# Read the most recent log entries from the file.
def get_recent_log_entries(limit: int = 50) -> list[str]:
    # Resolve the configured log file.
    log_file = get_log_file_path()
    # Return no logs if the file does not exist yet.
    if not log_file.exists():
        return []

    # Read all log lines.
    lines = log_file.read_text(encoding="utf-8").splitlines()
    # Reject non-positive limits.
    if limit <= 0:
        return []
    # Return the tail of the log file.
    return lines[-limit:]
