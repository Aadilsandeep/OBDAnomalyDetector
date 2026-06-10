"""
ml/health_score.py
==================
Vehicle health assessment engine for the AutoAssist OBD-II pipeline.

Pipeline position:

    Raw Telemetry → Preprocessing → State Classification
        → Feature Engineering → Anomaly Detection → **Health Score Engine**

Responsibility
--------------
This module has exactly **one** responsibility: convert the anomaly-enriched
DataFrame produced by :class:`~server.ml.anomaly_detector.AnomalyDetector`
into a structured vehicle health assessment.

It does NOT:
- Train or retrain models
- Modify the anomaly detector
- Expose API endpoints
- Render frontend views

Input contract
--------------
A :class:`pandas.DataFrame` containing at minimum the two columns produced
by ``AnomalyDetector.detect()``:

- ``anomaly_score`` (float) — raw Isolation Forest decision function output
- ``anomaly_flag`` (int)   — binary label (0 = normal, 1 = anomaly)

Output contract
---------------
A plain :class:`dict` (JSON-serialisable) containing:

.. code-block:: python

    {
        "health_score":    float,   # 0.00 – 100.00
        "risk_level":      str,     # LOW | MODERATE | HIGH | CRITICAL
        "anomaly_rate":    float,   # 0.0 – 1.0
        "total_anomalies": int,
        "total_records":   int,
    }

Usage
-----
    from server.ml.health_score import HealthScoreEngine

    engine = HealthScoreEngine()
    result = engine.calculate(df_with_anomalies)

FastAPI integration
-------------------
``HealthScoreEngine`` is a plain Python class with no global mutable state.
Instantiate it once at application startup (e.g. in a ``lifespan`` handler)
and inject it into route handlers via ``Depends()``.  The ``calculate``
method is stateless and thread-safe for concurrent request serving.

Future expansion
----------------
The engine is designed to accommodate richer health assessments in later
phases — state distributions, aggressive-driving events, session-level
statistics, and per-sensor degradation signals — without breaking the
existing public interface.  New signals should be added as additional keys
in the returned dict, preserving backward compatibility.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

from server.ml.anomaly_detector import ANOMALY_FLAG_COLUMN, ANOMALY_SCORE_COLUMN

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk-level enumeration
# ---------------------------------------------------------------------------


class RiskLevel(enum.Enum):
    """Vehicle risk classification derived from the health score.

    Thresholds
    ----------
    =========  ==================
    Score      Level
    =========  ==================
    90 – 100   ``LOW``
    70 – 89    ``MODERATE``
    50 – 69    ``HIGH``
     0 – 49    ``CRITICAL``
    =========  ==================

    Using an ``Enum`` rather than raw strings provides type safety,
    IDE autocompletion, and prevents typo-induced bugs downstream.
    The ``.value`` is the human-readable label emitted in the output dict
    and serialised to JSON by FastAPI automatically.
    """

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Risk-level resolver
# ---------------------------------------------------------------------------


def _resolve_risk_level(health_score: float) -> RiskLevel:
    """Map a health score to its corresponding :class:`RiskLevel`.

    Parameters
    ----------
    health_score:
        A value in the range ``[0.0, 100.0]``.

    Returns
    -------
    RiskLevel
        The risk classification for the given score.
    """
    if health_score >= 90.0:
        return RiskLevel.LOW
    if health_score >= 70.0:
        return RiskLevel.MODERATE
    if health_score >= 50.0:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# Output dict keys — single source of truth for downstream consumers
# ---------------------------------------------------------------------------

HEALTH_SCORE_KEY: Final[str] = "health_score"
RISK_LEVEL_KEY: Final[str] = "risk_level"
ANOMALY_RATE_KEY: Final[str] = "anomaly_rate"
TOTAL_ANOMALIES_KEY: Final[str] = "total_anomalies"
TOTAL_RECORDS_KEY: Final[str] = "total_records"


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthScoreConfig:
    """Immutable configuration for :class:`HealthScoreEngine`.

    Keeping configuration in a dedicated frozen dataclass makes it trivial
    to serialise, log, and pass through FastAPI dependency injection without
    exposing constructor keyword arguments across the codebase.

    Attributes
    ----------
    score_precision:
        Number of decimal places to round the health score to.
    rate_precision:
        Number of decimal places to round the anomaly rate to.
    """

    score_precision: int = 2
    rate_precision: int = 4


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_input(df: pd.DataFrame) -> None:
    """Validate the input DataFrame before health-score calculation.

    Raises descriptive exceptions rather than allowing cryptic downstream
    errors to propagate.

    Parameters
    ----------
    df:
        DataFrame to validate.  Expected to be the output of
        ``AnomalyDetector.detect()``.

    Raises
    ------
    TypeError
        If *df* is not a :class:`pandas.DataFrame`.
    ValueError
        If *df* is empty or is missing the required anomaly columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"HealthScoreEngine.calculate expects a pandas DataFrame, "
            f"got {type(df).__name__!r} instead."
        )

    if df.empty:
        raise ValueError(
            "HealthScoreEngine.calculate received an empty DataFrame. "
            "Ensure the anomaly detection pipeline completed successfully "
            "before calculating health scores."
        )

    required_columns: list[str] = [ANOMALY_SCORE_COLUMN, ANOMALY_FLAG_COLUMN]
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame is missing required column(s): {sorted(missing)}. "
            f"Expected columns produced by AnomalyDetector.detect(): "
            f"{required_columns}."
        )

    logger.debug(
        "Health score input validation passed",
        extra={"rows": len(df), "columns": len(df.columns)},
    )


# ---------------------------------------------------------------------------
# HealthScoreEngine
# ---------------------------------------------------------------------------


class HealthScoreEngine:
    """Converts anomaly detection output into a vehicle health assessment.

    This engine consumes the DataFrame produced by
    :meth:`~server.ml.anomaly_detector.AnomalyDetector.detect` and returns
    a JSON-serialisable dict summarising overall vehicle health.

    Parameters
    ----------
    config:
        Optional :class:`HealthScoreConfig` instance.  If omitted,
        sensible production defaults are used.

    Examples
    --------
    >>> engine = HealthScoreEngine()
    >>> result = engine.calculate(df_with_anomalies)
    >>> result["health_score"]
    95.23
    >>> result["risk_level"]
    'LOW'
    """

    def __init__(
        self,
        config: HealthScoreConfig | None = None,
    ) -> None:
        self._config: HealthScoreConfig = config or HealthScoreConfig()

        logger.info(
            "HealthScoreEngine initialised",
            extra={
                "score_precision": self._config.score_precision,
                "rate_precision": self._config.rate_precision,
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(self, df: pd.DataFrame) -> dict[str, Any]:
        """Calculate a vehicle health assessment from anomaly detection output.

        Processing pipeline::

            DataFrame (from AnomalyDetector.detect())
                ↓
            Validation (not empty, required columns present)
                ↓
            Metric computation
                • total_records  = len(df)
                • total_anomalies = sum(anomaly_flag == 1)
                • anomaly_rate   = total_anomalies / total_records
                ↓
            Health score
                • health_score = max(0, 100 - anomaly_rate * 100)
                • Rounded to config.score_precision decimal places
                ↓
            Risk level classification
                • 90-100  → LOW
                • 70-89   → MODERATE
                • 50-69   → HIGH
                •  0-49   → CRITICAL
                ↓
            Return dict

        Parameters
        ----------
        df:
            DataFrame produced by ``AnomalyDetector.detect()``.  Must
            contain ``anomaly_score`` and ``anomaly_flag`` columns.

        Returns
        -------
        dict[str, Any]
            JSON-serialisable health assessment:

            - ``health_score`` (float): 0.00 – 100.00
            - ``risk_level`` (str): ``"LOW"`` | ``"MODERATE"`` |
              ``"HIGH"`` | ``"CRITICAL"``
            - ``anomaly_rate`` (float): 0.0 – 1.0
            - ``total_anomalies`` (int): count of anomaly flags == 1
            - ``total_records`` (int): total row count

        Raises
        ------
        TypeError
            If *df* is not a :class:`pandas.DataFrame`.
        ValueError
            If *df* is empty or missing required columns.
        """
        logger.info(
            "Health score calculation started",
            extra={"input_rows": len(df)},
        )

        # 1. Validate -------------------------------------------------------
        _validate_input(df)

        # 2. Core metrics ----------------------------------------------------
        total_records: int = len(df)
        total_anomalies: int = int(df[ANOMALY_FLAG_COLUMN].sum())
        anomaly_rate: float = total_anomalies / total_records

        # 3. Health score ----------------------------------------------------
        raw_score: float = 100.0 - (anomaly_rate * 100.0)
        health_score: float = round(
            max(0.0, raw_score),
            self._config.score_precision,
        )

        # 4. Risk level ------------------------------------------------------
        risk_level: RiskLevel = _resolve_risk_level(health_score)

        # 5. Assemble result -------------------------------------------------
        result: dict[str, Any] = {
            HEALTH_SCORE_KEY: health_score,
            RISK_LEVEL_KEY: risk_level.value,
            ANOMALY_RATE_KEY: round(anomaly_rate, self._config.rate_precision),
            TOTAL_ANOMALIES_KEY: total_anomalies,
            TOTAL_RECORDS_KEY: total_records,
        }

        logger.info(
            "Health score calculation complete",
            extra={
                "health_score": health_score,
                "risk_level": risk_level.value,
                "anomaly_rate": round(anomaly_rate, self._config.rate_precision),
                "total_anomalies": total_anomalies,
                "total_records": total_records,
            },
        )

        return result

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def config(self) -> HealthScoreConfig:
        """Return the active configuration (read-only — dataclass is frozen)."""
        return self._config

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HealthScoreEngine("
            f"score_precision={self._config.score_precision!r}, "
            f"rate_precision={self._config.rate_precision!r})"
        )
