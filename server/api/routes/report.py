"""
api/routes/report.py
====================
Executive report endpoint for the AutoAssist API.

``GET /api/sessions/{session_id}/report``

Returns:
- Health score summary
- Anomaly summary with severity breakdown
- Driving state distribution
- Rule-based executive insights
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import APIRouter, Depends

from server.api.dependencies import get_session
from server.api.schemas.report import (
    AnomalySummary,
    DrivingStateSummary,
    ReportResponse,
)
from server.api.services.enrichment import (
    SEVERITY_COLUMN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from server.api.services.report_service import generate_executive_insights
from server.api.services.session_service import SessionData

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Reports"])


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/api/sessions/{session_id}/report",
    response_model=ReportResponse,
    summary="Get executive report for a session",
)
async def get_report(
    session: SessionData = Depends(get_session),
) -> ReportResponse:
    """Assemble a comprehensive executive report from session data.

    Parameters
    ----------
    session:
        The resolved session data.

    Returns
    -------
    ReportResponse
        Complete report with health score, anomaly breakdown, driving
        states, and executive insights.
    """
    health: dict[str, Any] = session.health_result
    state = session.state_analysis
    df = session.df_enriched

    # -- Severity breakdown --
    severity_counts: dict[str, int] = {
        SEVERITY_LOW: 0,
        SEVERITY_MEDIUM: 0,
        SEVERITY_HIGH: 0,
        SEVERITY_CRITICAL: 0,
    }
    if SEVERITY_COLUMN in df.columns:
        anomaly_df = df[df["anomaly_flag"] == 1]
        counts = anomaly_df[SEVERITY_COLUMN].value_counts()
        for sev in severity_counts:
            severity_counts[sev] = int(counts.get(sev, 0))

    anomaly_summary = AnomalySummary(
        total=session.total_anomalies,
        critical=severity_counts[SEVERITY_CRITICAL],
        high=severity_counts[SEVERITY_HIGH],
        medium=severity_counts[SEVERITY_MEDIUM],
        low=severity_counts[SEVERITY_LOW],
    )

    # -- Driving states --
    driving_states = [
        DrivingStateSummary(name=name, percentage=pct)
        for name, pct in state.state_percentages.items()
        if pct > 0
    ]

    # -- Executive insights --
    insights = generate_executive_insights(
        health_result=health,
        state_analysis=state,
        df_enriched=df,
        total_anomalies=session.total_anomalies,
        total_records=session.total_records,
    )

    logger.info(
        "Report data assembled",
        extra={
            "session_id": session.session_id,
            "insight_count": len(insights),
        },
    )

    return ReportResponse(
        health_score=health.get("health_score", 0.0),
        risk_level=health.get("risk_level", "UNKNOWN"),
        anomaly_rate=health.get("anomaly_rate", 0.0),
        total_records=session.total_records,
        total_anomalies=session.total_anomalies,
        anomaly_summary=anomaly_summary,
        driving_states=driving_states,
        dominant_state=state.dominant_state,
        executive_insights=insights,
    )
