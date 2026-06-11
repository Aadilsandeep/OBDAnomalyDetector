"""
api/schemas/sensors.py
======================
Pydantic v2 response models for the ``GET /api/sessions/{session_id}/sensors``
endpoint.

Response shape is aligned with the frontend's ``mockData.ts`` structures:
- ``sensors`` — list of sensor labels
- ``correlation`` — NxN matrix of Pearson coefficients
- ``pairs`` — pre-computed scatter-plot data for top sensor pairs
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


class SensorPairPoint(CamelModel):
    """Single point in a pairwise sensor scatter plot."""

    x: float
    y: float


class SensorPair(CamelModel):
    """Pairwise relationship between two sensors."""

    id: str
    x_label: str
    y_label: str
    correlation: float
    data: list[SensorPairPoint]


class SensorsResponse(CamelModel):
    """Correlation matrix and pairwise sensor data for a session."""

    sensors: list[str]
    correlation: list[list[float]]
    pairs: list[SensorPair]
