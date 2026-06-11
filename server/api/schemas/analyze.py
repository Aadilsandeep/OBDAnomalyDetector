"""
api/schemas/analyze.py
======================
Pydantic v2 response models for the ``POST /api/analyze`` endpoint.
"""

from __future__ import annotations

from server.api.schemas._base import CamelModel


class AnalyzeResponse(CamelModel):
    """Response returned after a successful CSV analysis.

    Attributes
    ----------
    session_id:
        UUID4 string identifying the newly created session.
    status:
        Pipeline completion status (always ``"complete"`` on success).
    total_records:
        Total number of rows in the analysed DataFrame.
    total_anomalies:
        Count of rows flagged as anomalies.
    """

    session_id: str
    status: str
    total_records: int
    total_anomalies: int

    @classmethod
    def from_session(
        cls,
        session_id: str,
        total_records: int,
        total_anomalies: int,
    ) -> "AnalyzeResponse":
        """Factory method for creating a response from session data."""
        return cls(
            session_id=session_id,
            status="complete",
            total_records=total_records,
            total_anomalies=total_anomalies,
        )
