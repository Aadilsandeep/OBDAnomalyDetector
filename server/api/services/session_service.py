"""
api/services/session_service.py
================================
In-memory session store for the AutoAssist API.

Session lifecycle
-----------------
::

    CSV Upload → Analysis → Session Created → session_id
                                ↓
                    Frontend Queries Data via session_id

Each session holds the full analysis result (enriched DataFrame, health
assessment, state analysis, classification report) so that downstream
endpoints can serve data without re-running inference.

Design decisions
----------------
- **In-memory only** — no database, no persistence across restarts.
  This aligns with the current project scope and avoids unnecessary
  infrastructure.
- **Thread-safe via dict** — CPython's GIL makes dict reads/writes
  atomic for single operations.  If the application moves to a
  multi-process deployment, this should be replaced with a shared store.
- **UUID4 session IDs** — collision-resistant, URL-safe, no sequential
  information leakage.
- **Session data is immutable after creation** — once stored, analysis
  results are never modified.

Future compatibility
--------------------
- TTL-based eviction for memory management.
- Async Redis backend for multi-process deployments.
- Session metadata (creation time, file name, file size) for admin UIs.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final

import pandas as pd

from server.analytics.state_analyzer import StateAnalysisResult

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionData:
    """Immutable container for a completed analysis session.

    Attributes
    ----------
    session_id:
        Unique identifier for this session (UUID4 string).
    created_at:
        UTC timestamp of session creation.
    filename:
        Original filename of the uploaded CSV.
    df_enriched:
        The fully enriched DataFrame — contains the original columns
        plus feature engineering output, anomaly scores, anomaly flags,
        and severity labels.
    health_result:
        Dict produced by ``HealthScoreEngine.calculate()``.
    state_analysis:
        ``StateAnalysisResult`` from ``analyze_states()``.
    total_records:
        Total row count in the enriched DataFrame.
    total_anomalies:
        Count of rows where ``anomaly_flag == 1``.
    """

    session_id: str
    created_at: datetime
    filename: str
    df_enriched: pd.DataFrame
    health_result: dict[str, Any]
    state_analysis: StateAnalysisResult
    total_records: int
    total_anomalies: int


# ---------------------------------------------------------------------------
# SessionService
# ---------------------------------------------------------------------------


class SessionService:
    """In-memory session store for analysis results.

    Thread-safe for single-process deployments (CPython GIL).

    Examples
    --------
    >>> svc = SessionService()
    >>> session = svc.create_session(
    ...     filename="trip_001.csv",
    ...     df_enriched=df,
    ...     health_result=health,
    ...     state_analysis=analysis,
    ... )
    >>> svc.get_session(session.session_id)
    SessionData(...)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        logger.info("SessionService initialised (in-memory store)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(
        self,
        *,
        filename: str,
        df_enriched: pd.DataFrame,
        health_result: dict[str, Any],
        state_analysis: StateAnalysisResult,
    ) -> SessionData:
        """Create and store a new analysis session.

        Parameters
        ----------
        filename:
            Original name of the uploaded CSV file.
        df_enriched:
            Fully enriched DataFrame (anomaly scores + severity).
        health_result:
            Output of ``HealthScoreEngine.calculate()``.
        state_analysis:
            Output of ``analyze_states()``.

        Returns
        -------
        SessionData
            The newly created session.
        """
        session_id = str(uuid.uuid4())
        total_records = len(df_enriched)
        total_anomalies = int(df_enriched["anomaly_flag"].sum())

        session = SessionData(
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            filename=filename,
            df_enriched=df_enriched,
            health_result=health_result,
            state_analysis=state_analysis,
            total_records=total_records,
            total_anomalies=total_anomalies,
        )

        self._sessions[session_id] = session

        logger.info(
            "Session created",
            extra={
                "session_id": session_id,
                "upload_filename": filename,
                "total_records": total_records,
                "total_anomalies": total_anomalies,
            },
        )

        return session

    def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve a session by ID.

        Parameters
        ----------
        session_id:
            UUID4 string identifying the session.

        Returns
        -------
        SessionData | None
            The session data, or ``None`` if the session does not exist.
        """
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return lightweight metadata for all sessions.

        Returns
        -------
        list[dict[str, Any]]
            A list of dicts with ``sessionId``, ``filename``,
            ``createdAt``, ``totalRecords``, and ``totalAnomalies`` for
            each stored session, sorted by creation time descending.
        """
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )
        return [
            {
                "sessionId": s.session_id,
                "filename": s.filename,
                "createdAt": s.created_at.isoformat(),
                "totalRecords": s.total_records,
                "totalAnomalies": s.total_anomalies,
            }
            for s in sessions
        ]

    @property
    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)
