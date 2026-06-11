"""
api/routes/anomalies.py
=======================
Anomaly data endpoint for the AutoAssist API.

``GET /api/sessions/{session_id}/anomalies``

Returns:
- Individual anomaly events with enriched metadata
- Severity distribution (bar chart data)
- Anomaly heatmap (sensor group × time bucket matrix)
"""

from __future__ import annotations

import logging
import math
from typing import Final

import pandas as pd
from fastapi import APIRouter, Depends

from server.api.dependencies import get_session
from server.api.schemas.anomalies import (
    AnomaliesResponse,
    AnomalyEvent,
    SeverityBucket,
)
from server.api.services.enrichment import (
    SEVERITY_COLUMN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from server.api.services.session_service import SessionData

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Anomalies"])

# Sensor groups for the heatmap — maps canonical sensor columns to display groups.
_SENSOR_GROUPS: Final[dict[str, list[str]]] = {
    "Engine": ["rpm", "rpm_delta"],
    "Airflow": ["maf", "maf_delta"],
    "Intake": ["map", "map_delta"],
    "Throttle": ["throttle_pos", "throttle_delta"],
    "Speed": ["speed", "speed_delta"],
}

# Severity color mapping for the frontend bar chart.
_SEVERITY_COLORS: Final[dict[str, str]] = {
    SEVERITY_LOW: "var(--success)",
    SEVERITY_MEDIUM: "var(--chart-1)",
    SEVERITY_HIGH: "var(--warning)",
    SEVERITY_CRITICAL: "var(--critical)",
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/api/sessions/{session_id}/anomalies",
    response_model=AnomaliesResponse,
    summary="Get anomaly data for a session",
)
async def get_anomalies(
    session: SessionData = Depends(get_session),
) -> AnomaliesResponse:
    """Assemble anomaly data from a stored analysis session.

    Parameters
    ----------
    session:
        The resolved session data (injected via ``get_session``).

    Returns
    -------
    AnomaliesResponse
        Anomaly events, severity distribution, and heatmap.
    """
    df = session.df_enriched
    anomaly_df = df[df["anomaly_flag"] == 1].copy()

    # -- Anomaly Events --
    events = _build_anomaly_events(anomaly_df)

    # -- Severity Distribution --
    severity_dist = _build_severity_distribution(anomaly_df)

    # -- Heatmap --
    groups = list(_SENSOR_GROUPS.keys())
    time_buckets, heatmap_matrix = _build_heatmap(anomaly_df, groups)

    logger.info(
        "Anomaly data assembled",
        extra={
            "session_id": session.session_id,
            "total_anomalies": len(events),
        },
    )

    return AnomaliesResponse(
        anomalies=events,
        severity_distribution=severity_dist,
        heatmap_time_buckets=time_buckets,
        heatmap_groups=groups,
        heatmap=heatmap_matrix,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_anomaly_events(
    anomaly_df: pd.DataFrame,
) -> list[AnomalyEvent]:
    """Convert anomaly rows into frontend-compatible event objects.

    Parameters
    ----------
    anomaly_df:
        DataFrame filtered to only anomaly rows.

    Returns
    -------
    list[AnomalyEvent]
        Sorted by anomaly score (most anomalous first).
    """
    if anomaly_df.empty:
        return []

    # Sort by anomaly score ascending (most anomalous = most negative first).
    sorted_df = anomaly_df.sort_values("anomaly_score", ascending=True)

    events: list[AnomalyEvent] = []
    for idx, (_, row) in enumerate(sorted_df.iterrows()):
        # Generate a human-readable timestamp from row index.
        row_index = int(row.name) if hasattr(row, "name") else idx
        minutes = row_index // 60
        seconds = row_index % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Determine which sensors are most deviated.
        sensors = _identify_anomalous_sensors(row)

        # Build description from severity and state.
        severity = str(row.get(SEVERITY_COLUMN, SEVERITY_LOW))
        state = str(row.get("state", "Unknown"))
        description = _generate_anomaly_description(severity, state, sensors)

        events.append(
            AnomalyEvent(
                id=f"A-{idx + 1:04d}",
                time=time_str,
                severity=severity,
                state=state,
                sensors=sensors,
                description=description,
                anomaly_score=round(float(row["anomaly_score"]), 4),
            )
        )

    return events


def _identify_anomalous_sensors(row: pd.Series) -> list[str]:
    """Identify which sensors contributed to an anomaly.

    Uses the delta features — sensors with the largest absolute deltas
    are most likely contributing to the anomaly.

    Parameters
    ----------
    row:
        A single anomaly row.

    Returns
    -------
    list[str]
        Up to 3 sensor labels, ordered by contribution.
    """
    delta_columns = {
        "rpm_delta": "RPM",
        "speed_delta": "Speed",
        "maf_delta": "MAF",
        "map_delta": "MAP",
        "throttle_delta": "Throttle",
    }

    scored: list[tuple[str, float]] = []
    for col, label in delta_columns.items():
        if col in row.index:
            val = abs(float(row[col])) if not pd.isna(row[col]) else 0.0
            scored.append((label, val))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [label for label, _ in scored[:3]]


def _generate_anomaly_description(
    severity: str, state: str, sensors: list[str]
) -> str:
    """Generate a human-readable description for an anomaly event."""
    sensor_str = " and ".join(sensors[:2]) if sensors else "sensor readings"
    severity_word = {
        SEVERITY_LOW: "Minor",
        SEVERITY_MEDIUM: "Moderate",
        SEVERITY_HIGH: "Significant",
        SEVERITY_CRITICAL: "Critical",
    }.get(severity, "Notable")

    return f"{severity_word} deviation in {sensor_str} during {state.lower()}"


def _build_severity_distribution(
    anomaly_df: pd.DataFrame,
) -> list[SeverityBucket]:
    """Count anomalies per severity tier for the bar chart."""
    if anomaly_df.empty or SEVERITY_COLUMN not in anomaly_df.columns:
        return [
            SeverityBucket(name=s, value=0, color=_SEVERITY_COLORS.get(s, ""))
            for s in [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]
        ]

    counts = anomaly_df[SEVERITY_COLUMN].value_counts()
    return [
        SeverityBucket(
            name=severity,
            value=int(counts.get(severity, 0)),
            color=_SEVERITY_COLORS.get(severity, "var(--chart-1)"),
        )
        for severity in [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]
    ]


def _build_heatmap(
    anomaly_df: pd.DataFrame,
    groups: list[str],
    num_buckets: int = 8,
) -> tuple[list[str], list[list[int]]]:
    """Build an anomaly density heatmap (sensor group × time bucket).

    Divides the session timeline into ``num_buckets`` equal-width time
    windows.  For each group, counts anomalies in each time bucket.

    Parameters
    ----------
    anomaly_df:
        DataFrame filtered to anomaly rows only.
    groups:
        Ordered sensor group labels.
    num_buckets:
        Number of time divisions.

    Returns
    -------
    tuple[list[str], list[list[int]]]
        ``(time_bucket_labels, matrix)`` where ``matrix[i][j]`` is the
        anomaly count for group ``i`` in time bucket ``j``.
    """
    if anomaly_df.empty:
        labels = [f"{i * (120 // num_buckets):02d}:00" for i in range(num_buckets)]
        return labels, [[0] * num_buckets for _ in groups]

    # Use DataFrame index position as a proxy for time.
    total_rows = anomaly_df.index.max() + 1 if len(anomaly_df) > 0 else 1
    bucket_size = max(1, math.ceil(total_rows / num_buckets))

    # Generate time bucket labels.
    labels: list[str] = []
    for b in range(num_buckets):
        start_row = b * bucket_size
        minutes = start_row // 60
        labels.append(f"{minutes:02d}:{(start_row % 60):02d}")

    # Assign each anomaly row to a time bucket.
    anomaly_df = anomaly_df.copy()
    anomaly_df["_bucket"] = anomaly_df.index // bucket_size
    anomaly_df["_bucket"] = anomaly_df["_bucket"].clip(upper=num_buckets - 1)

    # Build matrix.
    matrix: list[list[int]] = []
    for group_name in groups:
        group_cols = _SENSOR_GROUPS.get(group_name, [])
        row_counts: list[int] = []
        for b in range(num_buckets):
            bucket_anomalies = anomaly_df[anomaly_df["_bucket"] == b]
            # Count anomalies where any sensor in this group has a large delta.
            count = 0
            for _, arow in bucket_anomalies.iterrows():
                for col in group_cols:
                    if col in arow.index and not pd.isna(arow[col]):
                        if "_delta" in col and abs(float(arow[col])) > 0:
                            count += 1
                            break
            row_counts.append(count)
        matrix.append(row_counts)

    return labels, matrix
