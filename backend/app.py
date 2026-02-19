"""
Ring Parser Backend Application
Main entry point for the FastAPI web service
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.api import routes

from backend.config import CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events (startup and shutdown hooks)

    This context manager handles initialization and cleanup tasks for the application.
    Code before yield runs on startup, code after yield runs on shutdown.
    """
    # Startup: Display welcome message and API documentation URL
    print("RingParser application started")
    print(f"API documentation available at: http://localhost:8000/docs")
    yield
    # Shutdown: Log cleanup message
    print("RingParser application shutting down")


# ============================================================================
# FastAPI Application Initialization
# ============================================================================

app = FastAPI(
    title="RingParser",
    description="Web application for mapping files to XSD schema and generating XML output",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# Enable CORS (Cross-Origin Resource Sharing) to allow frontend to communicate with backend
# Current settings allow all origins for local development (not recommended for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)


# ============================================================================
# API Routes Configuration
# ============================================================================

# Include all API routes from the routes module with /api prefix
# This makes all API endpoints available at /api/[endpoint]
app.include_router(routes.router, prefix="/api")


# ============================================================================
# Frontend Static Files Serving
# ============================================================================

# Serve the frontend HTML/CSS/JS files from the frontend directory
# This mounts the static files at the root path (/) so the frontend can be accessed at http://localhost:8000
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    # Mount static files with html=True to serve index.html for routing
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
