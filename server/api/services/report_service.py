"""
api/services/report_service.py
===============================
Rule-based executive insight generator for the AutoAssist API.

This service transforms analysis data into human-readable narrative
insights suitable for the Reports page.  All insights are deterministic
and rule-based — no LLM integration.

Rules are ordered by priority and evaluated against the session's health
score, anomaly distribution, driving state percentages, and severity
breakdown.  Each rule that matches contributes one insight line.

Design decisions
----------------
- Rules are pure functions that receive structured data and return
  ``str | None`` — ``None`` means the rule did not fire.
- The service is stateless and can be called concurrently.
- Insights match the ``executiveInsights`` shape in the frontend
  (``client/src/lib/mockData.ts`` line 185) — a simple string list.

Future compatibility
--------------------
- Per-vehicle calibration of thresholds.
- Configurable insight templates via JSON config.
- Severity-weighted insights for fleet dashboards.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from server.analytics.state_analyzer import StateAnalysisResult
from server.api.services.enrichment import (
    SEVERITY_COLUMN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

import pandas as pd

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------


def _insight_health_status(health_score: float, **_: Any) -> str | None:
    """Overall health narrative."""
    if health_score >= 90:
        return "Vehicle health remains stable across the session with no significant degradation."
    if health_score >= 70:
        return "Vehicle health is generally acceptable but shows signs of moderate stress."
    if health_score >= 50:
        return "Vehicle health is below optimal — review anomaly details for root cause analysis."
    return "Vehicle health is in critical condition — immediate inspection recommended."


def _insight_anomaly_count(
    total_anomalies: int, total_records: int, **_: Any
) -> str | None:
    """Anomaly volume narrative."""
    if total_anomalies == 0:
        return "No anomalies detected across the entire session."
    rate = total_anomalies / total_records if total_records > 0 else 0
    if rate < 0.01:
        return f"Only {total_anomalies} anomalies detected ({rate:.1%} of records) — within normal operating range."
    if rate < 0.05:
        return f"{total_anomalies} anomalies detected ({rate:.1%}) — elevated but not critical."
    return f"{total_anomalies} anomalies detected ({rate:.1%}) — significantly above baseline."


def _insight_dominant_state(state_analysis: StateAnalysisResult, **_: Any) -> str | None:
    """Driving state distribution narrative."""
    dominant = state_analysis.dominant_state
    pct = state_analysis.state_percentages.get(dominant, 0)
    return f"{dominant} was the dominant driving condition, accounting for {pct}% of the session."


def _insight_aggressive_driving(
    state_analysis: StateAnalysisResult, **_: Any
) -> str | None:
    """Aggressive driving narrative."""
    aggressive = state_analysis.aggressive_events
    total = state_analysis.total_rows
    if total == 0:
        return None
    pct = round(100.0 * aggressive / total, 1)
    if pct > 30:
        return f"High frequency of acceleration/deceleration events ({pct}%) — suggests aggressive driving patterns."
    if pct > 15:
        return f"Moderate acceleration/deceleration activity ({pct}%) observed during the session."
    return f"Smooth driving profile with only {pct}% acceleration/deceleration events."


def _insight_severity_breakdown(severity_counts: dict[str, int], **_: Any) -> str | None:
    """Critical/High severity narrative."""
    critical = severity_counts.get(SEVERITY_CRITICAL, 0)
    high = severity_counts.get(SEVERITY_HIGH, 0)
    if critical > 0:
        return f"{critical} critical anomaly event(s) detected — prioritise review of these incidents."
    if high > 0:
        return f"{high} high-severity anomaly event(s) detected — monitor closely over next sessions."
    return None


def _insight_anomaly_state_correlation(
    df_enriched: pd.DataFrame, **_: Any
) -> str | None:
    """Which driving state has the most anomalies."""
    anomalies = df_enriched[df_enriched["anomaly_flag"] == 1]
    if anomalies.empty or "state" not in anomalies.columns:
        return None

    state_counts = anomalies["state"].value_counts()
    if state_counts.empty:
        return None

    top_state = state_counts.index[0]
    top_count = int(state_counts.iloc[0])
    total = len(anomalies)
    pct = round(100.0 * top_count / total, 1)
    return f"{top_state} events account for {pct}% of all anomalies ({top_count}/{total})."


# Ordered list of all insight rules.
_INSIGHT_RULES: Final[list] = [
    _insight_health_status,
    _insight_anomaly_count,
    _insight_dominant_state,
    _insight_aggressive_driving,
    _insight_severity_breakdown,
    _insight_anomaly_state_correlation,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_executive_insights(
    *,
    health_result: dict[str, Any],
    state_analysis: StateAnalysisResult,
    df_enriched: pd.DataFrame,
    total_anomalies: int,
    total_records: int,
) -> list[str]:
    """Generate rule-based executive insights for a session report.

    Parameters
    ----------
    health_result:
        Output of ``HealthScoreEngine.calculate()``.
    state_analysis:
        Output of ``analyze_states()``.
    df_enriched:
        Fully enriched DataFrame (with severity column).
    total_anomalies:
        Total anomaly count for the session.
    total_records:
        Total record count for the session.

    Returns
    -------
    list[str]
        Ordered list of human-readable insight strings.
    """
    # Build severity counts from enriched data
    severity_counts: dict[str, int] = {}
    if SEVERITY_COLUMN in df_enriched.columns:
        severity_series = df_enriched.loc[
            df_enriched["anomaly_flag"] == 1, SEVERITY_COLUMN
        ].value_counts()
        severity_counts = severity_series.to_dict()

    context = {
        "health_score": health_result.get("health_score", 0.0),
        "total_anomalies": total_anomalies,
        "total_records": total_records,
        "state_analysis": state_analysis,
        "severity_counts": severity_counts,
        "df_enriched": df_enriched,
    }

    insights: list[str] = []
    for rule in _INSIGHT_RULES:
        try:
            result = rule(**context)
            if result is not None:
                insights.append(result)
        except Exception:
            logger.exception("Insight rule %s failed — skipping", rule.__name__)

    logger.info(
        "Executive insights generated",
        extra={"insight_count": len(insights)},
    )

    return insights
