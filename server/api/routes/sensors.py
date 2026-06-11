"""
api/routes/sensors.py
=====================
Sensor correlation endpoint for the AutoAssist API.

``GET /api/sessions/{session_id}/sensors``

Returns:
- Pearson correlation matrix across primary sensors
- Pre-computed pairwise scatter-plot data for key sensor pairs

**This computation belongs in the API layer** — it does not modify any
ML module.  The correlation matrix is calculated fresh from the session
DataFrame using ``pandas.DataFrame.corr()``.
"""

from __future__ import annotations

import logging
from typing import Final

import pandas as pd
from fastapi import APIRouter, Depends

from server.api.dependencies import get_session
from server.api.schemas.sensors import (
    SensorPair,
    SensorPairPoint,
    SensorsResponse,
)
from server.api.services.session_service import SessionData

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Sensors"])

# Sensor columns and their display labels.
_SENSOR_MAP: Final[dict[str, str]] = {
    "rpm": "RPM",
    "speed": "Speed",
    "throttle_pos": "Throttle",
    "map": "MAP",
    "maf": "MAF",
}

# Pre-defined sensor pairs for scatter plots.
_SENSOR_PAIRS: Final[list[tuple[str, str, str, str]]] = [
    ("rpm-speed", "rpm", "speed", "RPM"),
    ("rpm-maf", "rpm", "maf", "RPM"),
    ("throttle-rpm", "throttle_pos", "rpm", "Throttle"),
    ("speed-map", "speed", "map", "Speed"),
]

# Maximum scatter points per pair.
_MAX_SCATTER_POINTS: Final[int] = 500


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/api/sessions/{session_id}/sensors",
    response_model=SensorsResponse,
    summary="Get sensor correlations for a session",
)
async def get_sensors(
    session: SessionData = Depends(get_session),
) -> SensorsResponse:
    """Compute sensor correlation matrix and pairwise relationships.

    Parameters
    ----------
    session:
        The resolved session data.

    Returns
    -------
    SensorsResponse
        Correlation matrix and scatter-plot data.
    """
    df = session.df_enriched

    # Filter to available sensor columns.
    available_cols = [col for col in _SENSOR_MAP if col in df.columns]
    sensor_labels = [_SENSOR_MAP[col] for col in available_cols]

    # -- Correlation Matrix --
    if available_cols:
        corr_df = df[available_cols].corr(method="pearson")
        correlation_matrix = [
            [round(float(corr_df.iloc[i, j]), 2) for j in range(len(available_cols))]
            for i in range(len(available_cols))
        ]
    else:
        correlation_matrix = []

    # -- Pairwise Scatter Data --
    pairs = _build_sensor_pairs(df, available_cols, corr_df if available_cols else None)

    logger.info(
        "Sensor data assembled",
        extra={
            "session_id": session.session_id,
            "sensor_count": len(available_cols),
            "pair_count": len(pairs),
        },
    )

    return SensorsResponse(
        sensors=sensor_labels,
        correlation=correlation_matrix,
        pairs=pairs,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_sensor_pairs(
    df: pd.DataFrame,
    available_cols: list[str],
    corr_df: pd.DataFrame | None,
) -> list[SensorPair]:
    """Build pairwise sensor scatter-plot data.

    Parameters
    ----------
    df:
        The enriched DataFrame.
    available_cols:
        List of sensor columns available in the DataFrame.
    corr_df:
        Correlation DataFrame (may be None).

    Returns
    -------
    list[SensorPair]
        Scatter data for each configured sensor pair.
    """
    pairs: list[SensorPair] = []

    for pair_id, x_col, y_col, x_label in _SENSOR_PAIRS:
        if x_col not in available_cols or y_col not in available_cols:
            continue

        y_label = _SENSOR_MAP.get(y_col, y_col.upper())

        # Compute correlation coefficient.
        corr_value = 0.0
        if corr_df is not None and x_col in corr_df.columns and y_col in corr_df.columns:
            corr_value = round(float(corr_df.loc[x_col, y_col]), 2)

        # Sample data for scatter plot.
        pair_df = df[[x_col, y_col]].dropna()
        stride = max(1, len(pair_df) // _MAX_SCATTER_POINTS)
        sampled = pair_df.iloc[::stride]

        data = [
            SensorPairPoint(
                x=round(float(row[x_col]), 2),
                y=round(float(row[y_col]), 2),
            )
            for _, row in sampled.iterrows()
        ]

        pairs.append(
            SensorPair(
                id=pair_id,
                x_label=x_label,
                y_label=y_label,
                correlation=corr_value,
                data=data,
            )
        )

    return pairs
