"""
api/routes/dashboard.py
=======================
Dashboard data endpoint for the AutoAssist API.

``GET /api/sessions/{session_id}/dashboard``

Returns the composite data needed to render the main dashboard:
- Vehicle identification
- Health score gauge
- Session statistics cards
- Driving state pie chart
- Health timeline line chart

All response fields use **camelCase** to align with the frontend.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import APIRouter, Depends

from server.api.dependencies import get_session
from server.api.schemas.dashboard import (
    DashboardResponse,
    DrivingState,
    HealthScoreData,
    HealthTimelinePoint,
    SessionStat,
    VehicleInfo,
)
from server.api.services.session_service import SessionData

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

# Chart color mapping — matches the frontend's CSS custom properties.
_STATE_COLORS: Final[dict[str, str]] = {
    "Cruising": "var(--chart-1)",
    "Acceleration": "var(--chart-2)",
    "Traffic": "var(--chart-3)",
    "Deceleration": "var(--chart-4)",
    "Idle": "var(--chart-5)",
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/api/sessions/{session_id}/dashboard",
    response_model=DashboardResponse,
    summary="Get dashboard data for a session",
)
async def get_dashboard(
    session: SessionData = Depends(get_session),
) -> DashboardResponse:
    """Assemble dashboard data from a stored analysis session.

    Parameters
    ----------
    session:
        The resolved session data (injected via ``get_session``).

    Returns
    -------
    DashboardResponse
        Complete dashboard data.
    """
    health: dict[str, Any] = session.health_result
    state = session.state_analysis
    df = session.df_enriched

    # -- Vehicle Info --
    session_label = f"Session · {session.created_at.strftime('%b %d, %Y %H:%M')}"
    vehicle_info = VehicleInfo(
        name="OBD-II Vehicle",
        session=session_label,
        dataset=session.filename,
        dataset_status="Loaded",
        analysis_status="Complete",
    )

    # -- Health Score --
    score = health.get("health_score", 0.0)
    risk = health.get("risk_level", "UNKNOWN")
    status_map = {"LOW": "Healthy", "MODERATE": "Monitor", "HIGH": "Warning", "CRITICAL": "Critical"}
    health_score_data = HealthScoreData(
        score=score,
        status=status_map.get(risk, "Unknown"),
        risk_level=risk,
    )

    # -- Session Stats --
    anomaly_rate = health.get("anomaly_rate", 0.0)
    session_stats = [
        SessionStat(label="Records Processed", value=_format_number(session.total_records), trend="complete"),
        SessionStat(label="Detected Anomalies", value=str(session.total_anomalies), trend=f"{anomaly_rate:.1%} rate"),
        SessionStat(label="Health Score", value=str(int(score)), trend=risk.lower()),
        SessionStat(label="Dominant Condition", value=state.dominant_state, trend=f"{state.state_percentages.get(state.dominant_state, 0):.0f}% time"),
        SessionStat(label="Operational States", value=str(len([s for s, v in state.state_counts.items() if v > 0])), trend="stable"),
        SessionStat(label="Aggressive Events", value=_format_number(state.aggressive_events), trend="accel + decel"),
    ]

    # -- Driving States (pie chart) --
    driving_states = [
        DrivingState(
            name=s,
            value=state.state_percentages.get(s, 0.0),
            color=_STATE_COLORS.get(s, "var(--chart-1)"),
        )
        for s in state.state_percentages
        if state.state_percentages.get(s, 0) > 0
    ]

    # -- Health Timeline --
    # Compute a rolling window health snapshot across the session.
    health_timeline = _build_health_timeline(df, num_points=30)

    logger.info(
        "Dashboard data assembled",
        extra={"session_id": session.session_id},
    )

    return DashboardResponse(
        vehicle_info=vehicle_info,
        health_score=health_score_data,
        session_stats=session_stats,
        driving_states=driving_states,
        health_timeline=health_timeline,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_number(n: int) -> str:
    """Format a number with K/M suffixes for display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _build_health_timeline(
    df: Any,
    num_points: int = 30,
) -> list[HealthTimelinePoint]:
    """Build a health timeline by sampling the DataFrame into windows.

    Each window computes a local health score (100 - anomaly_rate * 100)
    and counts anomalies within that window.

    Parameters
    ----------
    df:
        The enriched DataFrame.
    num_points:
        Number of timeline points to generate.

    Returns
    -------
    list[HealthTimelinePoint]
        Timeline data points.
    """
    import pandas as pd

    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    total = len(df)
    window_size = max(1, total // num_points)
    points: list[HealthTimelinePoint] = []

    for i in range(num_points):
        start = i * window_size
        end = min(start + window_size, total)
        if start >= total:
            break

        window = df.iloc[start:end]
        anomaly_count = int(window["anomaly_flag"].sum())
        window_total = len(window)
        local_rate = anomaly_count / window_total if window_total > 0 else 0
        local_health = round(max(0.0, 100.0 - local_rate * 100.0), 1)

        points.append(
            HealthTimelinePoint(
                index=i,
                health=local_health,
                anomalies=anomaly_count,
            )
        )

    return points
