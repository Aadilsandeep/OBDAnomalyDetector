"""
api/routes/telemetry.py
=======================
Sensor time-series endpoint for the AutoAssist API.

``GET /api/sessions/{session_id}/telemetry``

Returns time-series data for the five primary sensors:
RPM, Speed, MAF, MAP, Throttle.

Response shape matches the frontend's ``telemetry`` object in
``mockData.ts`` — each sensor is an array of ``{t, v}`` points.
"""

from __future__ import annotations

import logging
from typing import Final

import pandas as pd
from fastapi import APIRouter, Depends, Query

from server.api.dependencies import get_session
from server.api.schemas.telemetry import TelemetryPoint, TelemetryResponse
from server.api.services.session_service import SessionData

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Telemetry"])

# Sensor column → display config.
_SENSOR_COLUMNS: Final[dict[str, str]] = {
    "rpm": "rpm",
    "speed": "speed",
    "maf": "maf",
    "map": "map",
    "throttle_pos": "throttle",
}

# Maximum points to return (prevents massive payloads).
_MAX_POINTS: Final[int] = 2000


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/api/sessions/{session_id}/telemetry",
    response_model=TelemetryResponse,
    summary="Get sensor time-series for a session",
)
async def get_telemetry(
    session: SessionData = Depends(get_session),
    max_points: int = Query(
        default=_MAX_POINTS,
        ge=10,
        le=10000,
        description="Maximum number of data points per sensor.",
    ),
) -> TelemetryResponse:
    """Extract sensor time-series from the session DataFrame.

    If the dataset has more rows than ``max_points``, the data is
    down-sampled using uniform stride selection to preserve the shape
    of the signal.

    Parameters
    ----------
    session:
        The resolved session data.
    max_points:
        Maximum points per sensor (query parameter).

    Returns
    -------
    TelemetryResponse
        Time-series data for each sensor.
    """
    df = session.df_enriched
    total = len(df)

    # Down-sample if necessary.
    stride = max(1, total // max_points)
    sampled = df.iloc[::stride].reset_index(drop=True)

    series: dict[str, list[TelemetryPoint]] = {}

    for col, key in _SENSOR_COLUMNS.items():
        if col in sampled.columns:
            points = [
                TelemetryPoint(t=i, v=round(float(row[col]), 2))
                for i, (_, row) in enumerate(sampled.iterrows())
                if not pd.isna(row[col])
            ]
            series[key] = points
        else:
            series[key] = []

    logger.info(
        "Telemetry data assembled",
        extra={
            "session_id": session.session_id,
            "total_rows": total,
            "sampled_rows": len(sampled),
            "stride": stride,
        },
    )

    return TelemetryResponse(
        rpm=series.get("rpm", []),
        speed=series.get("speed", []),
        maf=series.get("maf", []),
        map=series.get("map", []),
        throttle=series.get("throttle", []),
    )
