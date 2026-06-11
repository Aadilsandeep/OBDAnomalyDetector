"""
api/schemas/anomalies.py
========================
Pydantic v2 response models for the ``GET /api/sessions/{session_id}/anomalies``
endpoint.

Response shape is aligned with the frontend's ``mockData.ts`` structures:
- ``anomalies`` — list of individual anomaly events
- ``severityDistribution`` — count per severity tier
- ``heatmap`` / ``heatmapGroups`` / ``heatmapTimeBuckets`` — anomaly density
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class AnomalyEvent(CamelModel):
    """Single anomaly event with enriched metadata.

    Mirrors the shape of elements in ``mockData.anomalies``.
    """

    id: str
    time: str
    severity: str
    state: str
    sensors: list[str]
    description: str
    anomaly_score: float


class SeverityBucket(CamelModel):
    """Anomaly count for a single severity tier."""

    name: str
    value: int
    color: str


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class AnomaliesResponse(CamelModel):
    """Complete anomaly data for a session."""

    anomalies: list[AnomalyEvent]
    severity_distribution: list[SeverityBucket]
    heatmap_time_buckets: list[str]
    heatmap_groups: list[str]
    heatmap: list[list[int]]
