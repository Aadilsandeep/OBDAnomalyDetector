"""
api/main.py
===========
FastAPI application factory for the AutoAssist OBD-II platform.

Responsibilities
----------------
- Create the FastAPI application with metadata and CORS configuration.
- Define a ``lifespan`` context manager that loads ML models once at
  startup and stores them in ``app.state``.
- Register all route modules.
- Configure structured logging.

Usage
-----
::

    # Development
    uvicorn server.api.main:app --reload --host 0.0.0.0 --port 8000

    # Production
    uvicorn server.api.main:app --host 0.0.0.0 --port 8000 --workers 1

Important
---------
The ``AnomalyDetector`` and ``HealthScoreEngine`` are loaded **once** in
the lifespan handler and reused across all requests.  Models are never
reloaded per-request.

Since the models are loaded into Python process memory and are not
thread-safe for concurrent writes (though reads are safe), production
deployments should use ``--workers 1`` or ensure the framework's
concurrency model protects shared state.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Final

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api.routes import analyze, anomalies, dashboard, report, sensors, telemetry
from server.api.services.session_service import SessionService
from server.ml.anomaly_detector import AnomalyDetector
from server.ml.health_score import HealthScoreEngine

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — model loading at startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager.

    **Startup**: Load ML models and initialise services.
    **Shutdown**: Log shutdown and clean up.

    All heavyweight objects are stored in ``app.state`` so that
    dependency injection providers in ``dependencies.py`` can
    retrieve them without global mutable state.
    """
    # -- Startup ---------------------------------------------------------
    logger.info("AutoAssist API starting up — loading ML models...")

    try:
        detector = AnomalyDetector()
        logger.info("AnomalyDetector loaded successfully")
    except FileNotFoundError as exc:
        logger.error("Failed to load AnomalyDetector: %s", exc)
        raise

    try:
        health_engine = HealthScoreEngine()
        logger.info("HealthScoreEngine loaded successfully")
    except Exception as exc:
        logger.error("Failed to load HealthScoreEngine: %s", exc)
        raise

    session_service = SessionService()

    # Store in application state for dependency injection.
    app.state.detector = detector
    app.state.health_engine = health_engine
    app.state.session_service = session_service

    logger.info(
        "AutoAssist API ready — models loaded, session service initialised"
    )

    yield

    # -- Shutdown --------------------------------------------------------
    logger.info("AutoAssist API shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


app = FastAPI(
    title="AutoAssist OBD-II API",
    description=(
        "RESTful API exposing the AutoAssist anomaly detection pipeline. "
        "Upload OBD-II CSV files, run inference, and query analysis results."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS — allow TanStack Start server functions to call the API
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a structured JSON error.

    This prevents stack traces from leaking to the client while still
    logging the full error for debugging.
    """
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Check server logs for details.",
        },
    )


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

app.include_router(analyze.router)
app.include_router(dashboard.router)
app.include_router(anomalies.router)
app.include_router(telemetry.router)
app.include_router(sensors.router)
app.include_router(report.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """System health check endpoint."""
    return {"status": "ok", "service": "autoassist-api"}


@app.get("/api/sessions", tags=["Sessions"])
async def list_sessions(request: Request) -> list[dict]:
    """List all active analysis sessions."""
    service: SessionService = request.app.state.session_service
    return service.list_sessions()
