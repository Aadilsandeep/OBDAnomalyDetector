"""
api/schemas/dashboard.py
========================
Pydantic v2 response models for the ``GET /api/sessions/{session_id}/dashboard``
endpoint.

Response shape is aligned with the frontend's ``mockData.ts`` structures:
- ``vehicleInfo``
- ``healthScore``
- ``sessionStats``
- ``drivingStates``
- ``healthTimeline``
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class VehicleInfo(CamelModel):
    """Vehicle and session identification metadata."""

    name: str
    session: str
    dataset: str
    dataset_status: str
    analysis_status: str


class HealthScoreData(CamelModel):
    """Overall vehicle health score."""

    score: float
    status: str
    risk_level: str


class SessionStat(CamelModel):
    """Single session statistic card."""

    label: str
    value: str
    trend: str


class DrivingState(CamelModel):
    """Driving state distribution slice."""

    name: str
    value: float
    color: str


class HealthTimelinePoint(CamelModel):
    """Single point in the health timeline chart."""

    index: int
    health: float
    anomalies: int


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class DashboardResponse(CamelModel):
    """Complete dashboard data for a session."""

    vehicle_info: VehicleInfo
    health_score: HealthScoreData
    session_stats: list[SessionStat]
    driving_states: list[DrivingState]
    health_timeline: list[HealthTimelinePoint]
