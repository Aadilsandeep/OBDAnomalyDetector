"""
analytics/state_classifier.py
==============================
Rule-based driving-state classifier for the AutoAssist analytics platform.

This module receives a fully preprocessed OBD-II DataFrame (post-load,
standardisation, cleaning and merge) and assigns every row a single driving
state drawn from:

    Idle | Traffic | Cruising | Acceleration | Deceleration

Classification is **deterministic and rule-based** — no ML model is involved.
This makes the logic auditable, explainable, and straightforward to port to
embedded / real-time environments.

Classification priority (higher wins when multiple conditions match):
    1. Acceleration
    2. Deceleration
    3. Idle
    4. Cruising
    5. Traffic  ← fallback

Usage
-----
    from analytics.state_classifier import classify_states

    df_classified, report = classify_states(df_merged)
    report.log()

Future compatibility
--------------------
The module is structured so that:
    - Thresholds can be swapped out per-vehicle at call time.
    - ``_create_derived_features`` can be extended with rolling-window variants
      for live OBD-II streams.
    - Additional states can be inserted into the priority chain without
      touching unrelated logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Final

import pandas as pd

from server.analytics.state_definitions import (
    ACCEL_RPM_DELTA,
    ACCEL_SPEED_DELTA,
    CRUISE_SPEED_MIN,
    DECEL_RPM_DELTA,
    DECEL_SPEED_DELTA,
    IDLE_RPM_MIN,
    IDLE_SPEED_MAX,
)

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State label constants
# ---------------------------------------------------------------------------

STATE_IDLE: Final[str] = "Idle"
STATE_TRAFFIC: Final[str] = "Traffic"
STATE_CRUISING: Final[str] = "Cruising"
STATE_ACCELERATION: Final[str] = "Acceleration"
STATE_DECELERATION: Final[str] = "Deceleration"

# Column names used internally
_COL_STATE: Final[str] = "state"
_COL_SPEED_DELTA: Final[str] = "speed_delta"
_COL_RPM_DELTA: Final[str] = "rpm_delta"

# Minimum required input columns
_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset({
    "session_id",
    "speed",
    "rpm",
})


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class StateClassificationReport:
    """Summary of a single ``classify_states`` run.

    Mirrors the reporting pattern used by ``CleaningReport`` and
    ``MergeReport`` in the preprocessing pipeline.

    Attributes
    ----------
    rows_processed:
        Total number of rows in the input DataFrame.
    idle_count:
        Number of rows classified as *Idle*.
    traffic_count:
        Number of rows classified as *Traffic*.
    cruising_count:
        Number of rows classified as *Cruising*.
    acceleration_count:
        Number of rows classified as *Acceleration*.
    deceleration_count:
        Number of rows classified as *Deceleration*.
    """

    rows_processed: int = 0

    idle_count: int = 0
    traffic_count: int = 0
    cruising_count: int = 0
    acceleration_count: int = 0
    deceleration_count: int = 0

    # Private: populated automatically by classify_states
    _unclassified_count: int = field(default=0, repr=False)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def total_classified(self) -> int:
        """Sum of all state counts (should equal ``rows_processed``)."""
        return (
            self.idle_count
            + self.traffic_count
            + self.cruising_count
            + self.acceleration_count
            + self.deceleration_count
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self) -> None:
        """Emit a structured classification summary through the module logger.

        Logs at INFO level so the summary is always visible in standard
        pipeline runs.  Percentages are rounded to one decimal place.
        """
        logger.info("=" * 60)
        logger.info("State Classification Report")
        logger.info("=" * 60)
        logger.info("  Rows processed      : %d", self.rows_processed)
        logger.info("  Total classified    : %d", self.total_classified)

        if self._unclassified_count:
            logger.warning(
                "  Unclassified rows   : %d  ← fallback to Traffic",
                self._unclassified_count,
            )

        if self.rows_processed:
            pct = lambda n: round(100.0 * n / self.rows_processed, 1)  # noqa: E731
            logger.info("  %-20s %6d  (%s%%)", STATE_ACCELERATION, self.acceleration_count, pct(self.acceleration_count))
            logger.info("  %-20s %6d  (%s%%)", STATE_DECELERATION, self.deceleration_count, pct(self.deceleration_count))
            logger.info("  %-20s %6d  (%s%%)", STATE_IDLE,         self.idle_count,         pct(self.idle_count))
            logger.info("  %-20s %6d  (%s%%)", STATE_CRUISING,     self.cruising_count,     pct(self.cruising_count))
            logger.info("  %-20s %6d  (%s%%)", STATE_TRAFFIC,      self.traffic_count,      pct(self.traffic_count))

        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_input(df: pd.DataFrame) -> None:
    """Validate the input DataFrame before classification begins.

    Raises meaningful exceptions rather than letting cryptic pandas errors
    propagate to callers.

    Parameters
    ----------
    df:
        Object to validate.

    Raises
    ------
    TypeError
        If *df* is not a :class:`pandas.DataFrame`.
    ValueError
        If *df* is empty or is missing required columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"classify_states expects a pandas DataFrame, "
            f"got {type(df).__name__!r} instead."
        )

    if df.empty:
        raise ValueError(
            "classify_states received an empty DataFrame. "
            "Ensure the preprocessing pipeline completed successfully."
        )

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input DataFrame is missing required column(s): {sorted(missing)}. "
            f"Expected at minimum: {sorted(_REQUIRED_COLUMNS)}."
        )

    logger.debug("Input validation passed — %d rows, columns: %s", len(df), list(df.columns))


# ---------------------------------------------------------------------------
# Derived feature engineering
# ---------------------------------------------------------------------------


def _create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``speed_delta`` and ``rpm_delta`` columns to *df*.

    Both are computed independently within each driving session using:

    groupby("session_id").diff()

    This prevents artificial acceleration/deceleration events from being
    generated at session boundaries when multiple trips are merged into a
    single master dataset.

    These columns are intentionally kept in the returned DataFrame so that
    downstream analytics modules (e.g. smoothing, anomaly detection) can
    consume them without recomputation.

    Parameters
    ----------
    df:
        DataFrame that already contains ``speed`` and ``rpm`` columns.

    Returns
    -------
    pandas.DataFrame
        The same DataFrame with ``speed_delta`` and ``rpm_delta`` appended.
    """
    df[_COL_SPEED_DELTA] = (
    df.groupby("session_id")["speed"]
      .diff()
)

    df[_COL_RPM_DELTA] = (
        df.groupby("session_id")["rpm"]
        .diff()
    )

    logger.debug(
        "Derived features created — speed_delta range [%.2f, %.2f], "
        "rpm_delta range [%.2f, %.2f]",
        df[_COL_SPEED_DELTA].min(),
        df[_COL_SPEED_DELTA].max(),
        df[_COL_RPM_DELTA].min(),
        df[_COL_RPM_DELTA].max(),
    )

    return df


# ---------------------------------------------------------------------------
# Per-state classification helpers
# ---------------------------------------------------------------------------


def _classify_acceleration(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask identifying *Acceleration* rows.

    A row is classified as Acceleration when the vehicle is gaining speed or
    the engine is spinning up rapidly:

        speed_delta >= ACCEL_SPEED_DELTA  OR  rpm_delta >= ACCEL_RPM_DELTA

    Parameters
    ----------
    df:
        DataFrame with ``speed_delta`` and ``rpm_delta`` columns present.

    Returns
    -------
    pandas.Series[bool]
        ``True`` for every row that satisfies the Acceleration rule.
    """
    mask = (df[_COL_SPEED_DELTA] >= ACCEL_SPEED_DELTA) | (
        df[_COL_RPM_DELTA] >= ACCEL_RPM_DELTA
    )
    logger.debug("Acceleration mask — %d rows flagged", mask.sum())
    return mask


def _classify_deceleration(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask identifying *Deceleration* rows.

    A row is classified as Deceleration when the vehicle is losing speed or
    the engine is winding down rapidly:

        speed_delta <= DECEL_SPEED_DELTA  OR  rpm_delta <= DECEL_RPM_DELTA

    Note that ``DECEL_SPEED_DELTA`` and ``DECEL_RPM_DELTA`` should be
    configured as **negative** values in ``state_definitions``.

    Parameters
    ----------
    df:
        DataFrame with ``speed_delta`` and ``rpm_delta`` columns present.

    Returns
    -------
    pandas.Series[bool]
        ``True`` for every row that satisfies the Deceleration rule.
    """
    mask = (df[_COL_SPEED_DELTA] <= DECEL_SPEED_DELTA) | (
        df[_COL_RPM_DELTA] <= DECEL_RPM_DELTA
    )
    logger.debug("Deceleration mask — %d rows flagged", mask.sum())
    return mask


def _classify_idle(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask identifying *Idle* rows.

    A row is classified as Idle when the vehicle is stationary (or nearly so)
    but the engine is still running:

        speed <= IDLE_SPEED_MAX  AND  rpm > IDLE_RPM_MIN

    Parameters
    ----------
    df:
        DataFrame with ``speed`` and ``rpm`` columns present.

    Returns
    -------
    pandas.Series[bool]
        ``True`` for every row that satisfies the Idle rule.
    """
    mask = (df["speed"] <= IDLE_SPEED_MAX) & (df["rpm"] > IDLE_RPM_MIN)
    logger.debug("Idle mask — %d rows flagged", mask.sum())
    return mask


def _classify_cruising(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask identifying *Cruising* rows.

    A row is classified as Cruising when the vehicle is travelling above the
    cruise threshold with stable speed and RPM:

        speed > CRUISE_SPEED_MIN
        AND abs(speed_delta) < ACCEL_SPEED_DELTA
        AND abs(rpm_delta)   < ACCEL_RPM_DELTA

    Parameters
    ----------
    df:
        DataFrame with ``speed``, ``speed_delta``, and ``rpm_delta`` present.

    Returns
    -------
    pandas.Series[bool]
        ``True`` for every row that satisfies the Cruising rule.
    """
    mask = (
        (df["speed"] > CRUISE_SPEED_MIN)
        & (df[_COL_SPEED_DELTA].abs() < ACCEL_SPEED_DELTA)
        & (df[_COL_RPM_DELTA].abs() < ACCEL_RPM_DELTA)
    )
    logger.debug("Cruising mask — %d rows flagged", mask.sum())
    return mask


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_states(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, StateClassificationReport]:
    """Classify every row of *df* into exactly one driving state.

    This is the primary entry point for the state classifier.  It validates
    input, engineers derived features, applies classification rules in strict
    priority order, and returns an annotated copy of the DataFrame alongside
    a summary report.

    Classification priority
    -----------------------
    1. Acceleration  — most specific; evaluated first
    2. Deceleration
    3. Idle
    4. Cruising
    5. Traffic       — catch-all fallback

    The original DataFrame is **never mutated**.

    Parameters
    ----------
    df:
        Fully preprocessed OBD-II DataFrame produced by the preprocessing
        pipeline.  Must contain at minimum the columns ``speed`` and ``rpm``.

    Returns
    -------
    classified_df : pandas.DataFrame
        Copy of *df* with three new columns appended:
        - ``speed_delta`` — row-to-row speed difference (km/h per sample)
        - ``rpm_delta``   — row-to-row RPM difference
        - ``state``       — one of the five driving state labels
    report : StateClassificationReport
        Counts and percentages for each state, ready to be logged or
        serialised.

    Raises
    ------
    TypeError
        If *df* is not a :class:`pandas.DataFrame`.
    ValueError
        If *df* is empty or is missing required columns.

    Examples
    --------
    >>> df_classified, report = classify_states(df_merged)
    >>> report.log()
    >>> df_classified["state"].value_counts()
    """
    logger.info("Starting driving-state classification — %d input rows", len(df))

    # ------------------------------------------------------------------
    # 1. Validate
    # ------------------------------------------------------------------
    _validate_input(df)

    # ------------------------------------------------------------------
    # 2. Work on an explicit copy — never mutate the caller's DataFrame
    # ------------------------------------------------------------------
    result = df.copy()

    # ------------------------------------------------------------------
    # 3. Derive speed_delta and rpm_delta
    # ------------------------------------------------------------------
    result = _create_derived_features(result)

    # ------------------------------------------------------------------
    # 4. Initialise state column to the fallback (Traffic)
    #    This guarantees every row has a label, even NaN-delta rows.
    # ------------------------------------------------------------------
    result[_COL_STATE] = STATE_TRAFFIC

    # ------------------------------------------------------------------
    # 5. Apply states in reverse priority order so that higher-priority
    #    states overwrite lower-priority ones.
    #    (Traffic is already set; Cruising → Idle → Deceleration → Acceleration)
    # ------------------------------------------------------------------

    cruising_mask = _classify_cruising(result)
    result.loc[cruising_mask, _COL_STATE] = STATE_CRUISING

    idle_mask = _classify_idle(result)
    result.loc[idle_mask, _COL_STATE] = STATE_IDLE

    decel_mask = _classify_deceleration(result)
    result.loc[decel_mask, _COL_STATE] = STATE_DECELERATION

    accel_mask = _classify_acceleration(result)
    result.loc[accel_mask, _COL_STATE] = STATE_ACCELERATION

    # ------------------------------------------------------------------
    # 6. Build report
    # ------------------------------------------------------------------
    state_counts = result[_COL_STATE].value_counts()

    report = StateClassificationReport(
        rows_processed=len(result),
        idle_count=int(state_counts.get(STATE_IDLE, 0)),
        traffic_count=int(state_counts.get(STATE_TRAFFIC, 0)),
        cruising_count=int(state_counts.get(STATE_CRUISING, 0)),
        acceleration_count=int(state_counts.get(STATE_ACCELERATION, 0)),
        deceleration_count=int(state_counts.get(STATE_DECELERATION, 0)),
    )

    # Sanity check — total classified should match rows processed
    unclassified = report.rows_processed - report.total_classified
    if unclassified != 0:
        logger.warning(
            "%d row(s) did not receive a state label — this is a logic error.",
            unclassified,
        )
    report._unclassified_count = unclassified

    logger.info(
        "Classification complete — %d rows: %d Accel | %d Decel | "
        "%d Idle | %d Cruising | %d Traffic",
        report.rows_processed,
        report.acceleration_count,
        report.deceleration_count,
        report.idle_count,
        report.cruising_count,
        report.traffic_count,
    )

    return result, report