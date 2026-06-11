"""
api/schemas/telemetry.py
========================
Pydantic v2 response models for the ``GET /api/sessions/{session_id}/telemetry``
endpoint.

Response shape is aligned with the frontend's ``mockData.telemetry`` structure:
each sensor is a list of ``{t, v}`` points.
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


class TelemetryPoint(CamelModel):
    """Single time-series data point."""

    t: int
    v: float


class TelemetryResponse(CamelModel):
    """Sensor time-series data for a session.

    Each field contains an array of ``{t, v}`` points matching the
    frontend's ``telemetry`` structure in ``mockData.ts``.
    """

    rpm: list[TelemetryPoint]
    speed: list[TelemetryPoint]
    maf: list[TelemetryPoint]
    map: list[TelemetryPoint]
    throttle: list[TelemetryPoint]
