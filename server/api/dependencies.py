"""
api/dependencies.py
===================
FastAPI dependency injection providers for the AutoAssist API.

All heavyweight objects (ML models, services) are loaded once at startup
in the ``lifespan`` handler (see ``main.py``) and stored in
``app.state``.  The dependency functions in this module retrieve them
from the request's ``app.state`` and yield them to route handlers via
``Depends()``.

This pattern ensures:
- Models are loaded exactly once (no per-request loading).
- Route handlers declare dependencies explicitly.
- Unit testing can override dependencies easily.

Usage
-----
::

    from server.api.dependencies import get_detector, get_session_service

    @router.get("/example")
    async def example(
        detector: AnomalyDetector = Depends(get_detector),
        sessions: SessionService = Depends(get_session_service),
    ):
        ...
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import HTTPException, Request

from server.ml.anomaly_detector import AnomalyDetector
from server.ml.health_score import HealthScoreEngine
from server.api.services.session_service import SessionData, SessionService

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependency providers
# ---------------------------------------------------------------------------


def get_detector(request: Request) -> AnomalyDetector:
    """Provide the singleton ``AnomalyDetector`` from application state.

    Parameters
    ----------
    request:
        The current FastAPI request (injected automatically).

    Returns
    -------
    AnomalyDetector
        The pre-loaded detector instance.
    """
    return request.app.state.detector


def get_health_engine(request: Request) -> HealthScoreEngine:
    """Provide the singleton ``HealthScoreEngine`` from application state.

    Parameters
    ----------
    request:
        The current FastAPI request (injected automatically).

    Returns
    -------
    HealthScoreEngine
        The pre-loaded health score engine instance.
    """
    return request.app.state.health_engine


def get_session_service(request: Request) -> SessionService:
    """Provide the singleton ``SessionService`` from application state.

    Parameters
    ----------
    request:
        The current FastAPI request (injected automatically).

    Returns
    -------
    SessionService
        The in-memory session store.
    """
    return request.app.state.session_service


def get_session(
    session_id: str,
    request: Request,
) -> SessionData:
    """Retrieve a session by ID or raise HTTP 404.

    This is a convenience dependency that combines session lookup with
    error handling, avoiding repetitive boilerplate in every route.

    Parameters
    ----------
    session_id:
        UUID4 path parameter from the URL.
    request:
        The current FastAPI request (injected automatically).

    Returns
    -------
    SessionData
        The resolved session.

    Raises
    ------
    HTTPException
        404 if the session ID does not exist.
    """
    service: SessionService = request.app.state.session_service
    session = service.get_session(session_id)

    if session is None:
        logger.warning(
            "Session not found",
            extra={"session_id": session_id},
        )
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Upload a CSV first via POST /api/analyze.",
        )

    return session
