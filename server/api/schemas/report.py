"""
api/schemas/report.py
=====================
Pydantic v2 response models for the ``GET /api/sessions/{session_id}/report``
endpoint.

Response shape is aligned with the frontend's Reports page, which
displays:
- Health score summary
- Anomaly summary with severity breakdown
- Driving state distribution
- Executive insights (rule-based narrative strings)
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


class AnomalySummary(CamelModel):
    """Aggregated anomaly statistics for the report."""

    total: int
    critical: int
    high: int
    medium: int
    low: int


class DrivingStateSummary(CamelModel):
    """Driving state percentage for the report."""

    name: str
    percentage: float


class ReportResponse(CamelModel):
    """Complete session report data."""

    health_score: float
    risk_level: str
    anomaly_rate: float
    total_records: int
    total_anomalies: int
    anomaly_summary: AnomalySummary
    driving_states: list[DrivingStateSummary]
    dominant_state: str
    executive_insights: list[str]
