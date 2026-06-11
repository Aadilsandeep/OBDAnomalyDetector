"""
api/services/enrichment.py
==========================
Anomaly enrichment layer for the AutoAssist API.

The ML pipeline (``AnomalyDetector``) produces only two columns:

- ``anomaly_score`` — raw Isolation Forest decision function output
- ``anomaly_flag``  — binary 0/1

The frontend, however, requires richer semantic labels:

    Low · Medium · High · Critical

This module maps ``anomaly_score`` into those severity tiers using
**configurable thresholds** without modifying any ML module.

Design decisions
----------------
- Thresholds are defined in a frozen dataclass so they can be swapped at
  startup via environment config or feature flags.
- The enrichment function operates on a full DataFrame column (vectorised)
  for efficiency.
- Severity labels exactly match the ``Severity`` TypeScript type used by
  the frontend (``client/src/lib/mockData.ts`` line 75).

Future compatibility
--------------------
- Per-vehicle threshold profiles (e.g. older vehicles have tighter bands).
- Score normalisation (min-max or percentile-based).
- Real-time streaming enrichment on per-window DataFrames.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from server.ml.anomaly_detector import ANOMALY_FLAG_COLUMN, ANOMALY_SCORE_COLUMN

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity labels — must match client/src/lib/mockData.ts Severity type
# ---------------------------------------------------------------------------

SEVERITY_LOW: Final[str] = "Low"
SEVERITY_MEDIUM: Final[str] = "Medium"
SEVERITY_HIGH: Final[str] = "High"
SEVERITY_CRITICAL: Final[str] = "Critical"

SEVERITY_COLUMN: Final[str] = "severity"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichmentConfig:
    """Configurable thresholds for anomaly score → severity mapping.

    Isolation Forest ``decision_function()`` returns a float where **lower
    (more negative)** values indicate stronger anomalies.  The thresholds
    below partition the score axis into four severity tiers.

    Default calibration is based on empirical observation of the training
    data distribution.  Override at startup if the production score
    distribution differs.

    Attributes
    ----------
    medium_threshold:
        Scores below this (and ≥ ``high_threshold``) are classified as
        *Medium*.  Default ``-0.05``.
    high_threshold:
        Scores below this (and ≥ ``critical_threshold``) are classified as
        *High*.  Default ``-0.10``.
    critical_threshold:
        Scores below this are classified as *Critical*.  Default ``-0.15``.
    """

    medium_threshold: float = -0.05
    high_threshold: float = -0.10
    critical_threshold: float = -0.15


# ---------------------------------------------------------------------------
# Enrichment functions
# ---------------------------------------------------------------------------


def assign_severity(
    score: float,
    config: EnrichmentConfig | None = None,
) -> str:
    """Map a single anomaly score to a severity label.

    Parameters
    ----------
    score:
        Raw Isolation Forest decision function output.
    config:
        Optional threshold configuration.

    Returns
    -------
    str
        One of ``"Low"``, ``"Medium"``, ``"High"``, ``"Critical"``.
    """
    cfg = config or EnrichmentConfig()

    if score < cfg.critical_threshold:
        return SEVERITY_CRITICAL
    if score < cfg.high_threshold:
        return SEVERITY_HIGH
    if score < cfg.medium_threshold:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def enrich_anomalies(
    df: pd.DataFrame,
    config: EnrichmentConfig | None = None,
) -> pd.DataFrame:
    """Add a ``severity`` column to an anomaly-enriched DataFrame.

    Only rows flagged as anomalies (``anomaly_flag == 1``) receive a
    severity classification.  Normal rows receive ``None`` (null) in the
    severity column.

    The function operates **on a copy** — the caller's DataFrame is never
    mutated.

    Parameters
    ----------
    df:
        DataFrame produced by ``AnomalyDetector.detect()``, containing at
        minimum ``anomaly_score`` and ``anomaly_flag`` columns.
    config:
        Optional threshold configuration.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with an additional ``severity`` column.

    Raises
    ------
    ValueError
        If required columns are missing.
    """
    required = {ANOMALY_SCORE_COLUMN, ANOMALY_FLAG_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame missing required column(s) for enrichment: {sorted(missing)}"
        )

    cfg = config or EnrichmentConfig()
    result = df.copy()

    # Vectorised severity assignment using np.select for performance.
    scores = result[ANOMALY_SCORE_COLUMN]
    flags = result[ANOMALY_FLAG_COLUMN]

    conditions = [
        (flags == 1) & (scores < cfg.critical_threshold),
        (flags == 1) & (scores < cfg.high_threshold),
        (flags == 1) & (scores < cfg.medium_threshold),
        (flags == 1),  # remaining anomalies → Low
    ]
    choices = [SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW]

    result[SEVERITY_COLUMN] = np.select(conditions, choices, default=None)

    # Summary logging
    severity_counts = result.loc[flags == 1, SEVERITY_COLUMN].value_counts()
    logger.info(
        "Anomaly enrichment complete",
        extra={
            "total_anomalies": int(flags.sum()),
            "severity_distribution": severity_counts.to_dict(),
        },
    )

    return result
