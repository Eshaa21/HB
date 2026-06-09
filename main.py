# This file is the main entry point of the FastAPI application
# It starts the web server and sets up automatic data generation every 30 seconds

# Import asynccontextmanager to manage app startup and shutdown events
from contextlib import asynccontextmanager
from pathlib import Path

# Import BackgroundScheduler to run tasks in the background (data generation every 30 seconds)
from apscheduler.schedulers.background import BackgroundScheduler
# Import FastAPI to create the web application
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import initialize_database function from database.py - this creates tables when app starts
from database import initialize_database
# Import initialize_admin_database function from admin_database.py - creates admin credentials table
from admin_database import initialize_admin_database
# Import logging functions from logger_config.py - helps track what app is doing
from logger_config import get_logger, setup_logging
# Import all the route handlers that handle API requests
from routes.alerts import router as alerts_router  # handles alerts endpoints
from routes.analytics_routes import router as analytics_router  # handles analytics endpoints
from routes.infrastructure import router as infrastructure_router  # handles areas/pipelines endpoints
from routes.telemetry import router as telemetry_router  # handles water data endpoints
from routes.auth import router as auth_router  # handles authentication endpoints
# Import generate_all_pipeline_data from sensor_simulator.py - generates fake water data
from sensor_simulator import generate_all_pipeline_data

# Set up logging when app file loads
setup_logging()
# Create a logger object to write log messages for this file
logger = get_logger(__name__)

# Create scheduler object - this will run tasks in the background
# BackgroundScheduler runs periodic jobs in a separate thread while FastAPI continues serving API requests
scheduler = BackgroundScheduler()


# This function runs when app starts (startup) and when app stops (shutdown)
@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI startup/shutdown lifecycle - runs when app starts and stops
    
    Startup (when app starts):
        1. Set up logging
        2. Create SQLite database tables and add default Pune areas/pipelines
        3. Start the scheduler and make it run data generation every 30 seconds
    
    Shutdown (when app stops):
        Stop the scheduler so background thread stops properly
    """
    # Set up logging when app starts
    setup_logging()
    # Create database tables if they don't exist, add default areas and pipelines
    initialize_database()
    # Initialize admin database with default admin user if needed
    initialize_admin_database()

    # Check if scheduler is not already running
    if not scheduler.running:
        # Tell scheduler to run generate_all_pipeline_data function every 30 seconds
        # Called from: generate_all_pipeline_data function in sensor_simulator.py
        scheduler.add_job(
            generate_all_pipeline_data,  # the function to run
            "interval",  # run it at regular intervals
            minutes=30,  # run every 30 seconds (generates water data for all pipelines)
            id="generate_all_pipeline_data",  # unique name for this job
            replace_existing=True,  # replace if this job already exists
        )
        # Start the scheduler - now it will run the data generation job
        scheduler.start()
        # Write a log message saying scheduler started
        logger.info("Telemetry scheduler started")

    # Write a log message saying app started successfully
    logger.info("Application startup complete")
    # Yield control back to app - this lets the app run
    try:
        yield
    # This code runs when app is shutting down
    finally:
        # Check if scheduler is running
        if scheduler.running:
            # Stop the scheduler
            scheduler.shutdown(wait=False)
            # Write a log message saying scheduler stopped
            logger.info("Telemetry scheduler stopped")


# Create the FastAPI web application with some information about it
app = FastAPI(
    title="Smart Water Distribution & Leak Detection System",  # name shown in documentation
    description="FastAPI project for automatic area-wise water telemetry, leak detection, alerts, and analytics.",  # description shown in documentation
    version="2.0.0",  # version number
    lifespan=lifespan,  # use the lifespan function for startup/shutdown
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


# This endpoint is called when user visits the root path (/)
@app.get("/")
def home() -> dict[str, str]:
    """Return basic API health information - shows if the app is running"""
    return {
        "project": "Smart Water Distribution & Leak Detection System",  # name of project
        "status": "Running",  # status showing app is working
    }


@app.get("/ui")
def frontend_ui() -> FileResponse:
    """Serve the frontend dashboard."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/index")
def frontend_index() -> FileResponse:
    """Serve the frontend dashboard at /index."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/login")
def frontend_login() -> FileResponse:
    """Serve the frontend login page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manage")
def frontend_manage() -> FileResponse:
    """Serve the frontend management page."""
    return FileResponse(FRONTEND_DIR / "manage.html")


# Add telemetry routes - handles endpoints like /water-data, /generate-data
# Called from: routes/telemetry.py
app.include_router(telemetry_router)
# Add infrastructure routes - handles endpoints like /areas, /pipelines
# Called from: routes/infrastructure.py
app.include_router(infrastructure_router)
# Add alerts routes - handles endpoints like /alerts
# Called from: routes/alerts.py
app.include_router(alerts_router)
# Add analytics routes - handles endpoints like /analytics
# Called from: routes/analytics_routes.py
app.include_router(analytics_router)
# Add authentication routes - handles endpoints like /login
# Called from: routes/auth.py
app.include_router(auth_router)
