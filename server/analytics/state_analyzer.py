"""
analytics/state_analyzer.py
============================
Driving-state analyzer for the AutoAssist analytics platform.

This module receives a fully classified OBD-II DataFrame (post-preprocessing
and post-state-classification) and transforms row-level state labels into
dashboard-ready metrics and per-session summaries.

The analyzer is intentionally read-only: it never modifies the input
DataFrame, never reclassifies rows, and never adds state columns.  Its only
job is to aggregate and interpret the ``state`` column that
``state_classifier.py`` already produced.

Usage
-----
    from analytics.state_analyzer import analyze_states

    result, report = analyze_states(df_classified)
    report.log()

    # Dashboard-ready artefacts
    print(result.dominant_state)
    print(result.state_percentages)
    print(result.session_statistics)

Future compatibility
--------------------
- Additional driving states: add the label to ``_SUPPORTED_STATES``; all
  helpers pick it up automatically.
- Driver behaviour scoring / health scoring: consume ``aggressive_events``
  and ``session_statistics`` without touching this module.
- Real-time OBD-II streaming: wrap ``analyze_states`` in a sliding-window
  caller; the function itself is stateless.
- FastAPI: ``StateAnalysisResult`` is a plain dataclass — serialise it with
  ``dataclasses.asdict`` or a Pydantic adapter at the API layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Final

import pandas as pd

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported states — single source of truth
# ---------------------------------------------------------------------------

_SUPPORTED_STATES: Final[tuple[str, ...]] = (
    "Idle",
    "Traffic",
    "Cruising",
    "Acceleration",
    "Deceleration",
)

# Column name constants
_COL_SESSION: Final[str] = "session_id"
_COL_STATE: Final[str] = "state"

# Minimum required input columns
_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset({_COL_SESSION, _COL_STATE})


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class StateAnalysisResult:
    """Dashboard-ready output produced by a single ``analyze_states`` run.

    Attributes
    ----------
    total_rows:
        Total number of rows analysed.
    dominant_state:
        The state with the highest overall row count across the entire dataset.
    state_counts:
        Absolute row count per state, keyed by state label.
        Example::

            {"Cruising": 1617902, "Traffic": 722475, ...}

    state_percentages:
        Percentage share per state, rounded to two decimal places.
        Values should sum approximately to 100.
        Example::

            {"Cruising": 60.08, "Traffic": 26.83, ...}

    session_statistics:
        One row per ``session_id``.  Columns:
        ``session_id``, ``dominant_state``,
        ``Cruising_pct``, ``Traffic_pct``, ``Idle_pct``,
        ``Acceleration_pct``, ``Deceleration_pct``.
        Missing states are filled with ``0.0``.
    aggressive_events:
        Sum of Acceleration and Deceleration counts.  Intended as an input
        signal for downstream driving-style analysis and health scoring.
    """

    total_rows: int
    dominant_state: str
    state_counts: dict[str, int]
    state_percentages: dict[str, float]
    session_statistics: pd.DataFrame
    aggressive_events: int


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class StateAnalysisReport:
    """Lightweight summary of a single ``analyze_states`` run.

    Mirrors the reporting convention of ``CleaningReport``,
    ``MergeReport``, and ``StateClassificationReport``.

    Attributes
    ----------
    rows_analyzed:
        Total rows present in the input DataFrame.
    session_count:
        Number of distinct ``session_id`` values found.
    dominant_state:
        State label with the highest occurrence.
    aggressive_events:
        Combined Acceleration + Deceleration count.
    """

    rows_analyzed: int = 0
    session_count: int = 0
    dominant_state: str = ""
    aggressive_events: int = 0

    def log(self) -> None:
        """Emit a structured analysis summary through the module logger.

        Logs at INFO level so the summary is always visible in standard
        pipeline runs.
        """
        logger.info("=" * 60)
        logger.info("State Analysis Report")
        logger.info("=" * 60)
        logger.info("  Rows analysed       : %d", self.rows_analyzed)
        logger.info("  Sessions            : %d", self.session_count)
        logger.info("  Dominant state      : %s", self.dominant_state)
        logger.info("  Aggressive events   : %d", self.aggressive_events)
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_input(df: pd.DataFrame) -> None:
    """Validate the input DataFrame before analysis begins.

    Raises meaningful exceptions rather than allowing cryptic pandas errors
    to propagate to callers.

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
            f"analyze_states expects a pandas DataFrame, "
            f"got {type(df).__name__!r} instead."
        )

    if df.empty:
        raise ValueError(
            "analyze_states received an empty DataFrame. "
            "Ensure the classification pipeline completed successfully."
        )

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input DataFrame is missing required column(s): {sorted(missing)}. "
            f"Expected at minimum: {sorted(_REQUIRED_COLUMNS)}."
        )

    logger.debug(
        "Input validation passed — %d rows, %d columns",
        len(df),
        len(df.columns),
    )


# ---------------------------------------------------------------------------
# Private helper functions
# ---------------------------------------------------------------------------


def _get_state_counts(df: pd.DataFrame) -> dict[str, int]:
    """Compute the absolute row count for each supported state.

    States that are absent from *df* receive a count of ``0`` so that the
    returned dictionary always contains exactly the keys in
    ``_SUPPORTED_STATES``.

    Parameters
    ----------
    df:
        Classified DataFrame containing a ``state`` column.

    Returns
    -------
    dict[str, int]
        Mapping of state label → row count.
    """
    raw_counts: pd.Series = df[_COL_STATE].value_counts()

    counts = {state: int(raw_counts.get(state, 0)) for state in _SUPPORTED_STATES}

    unknown_states = set(raw_counts.index) - set(_SUPPORTED_STATES)
    if unknown_states:
        logger.warning(
            "Encountered %d unsupported state label(s) in data: %s",
            len(unknown_states),
            sorted(unknown_states),
        )

    logger.debug("State counts: %s", counts)
    return counts


def _get_state_percentages(
    counts: dict[str, int],
    total_rows: int,
) -> dict[str, float]:
    """Convert absolute state counts to percentage shares.

    Parameters
    ----------
    counts:
        Output of :func:`_get_state_counts`.
    total_rows:
        Total number of rows in the DataFrame (used as the denominator).

    Returns
    -------
    dict[str, float]
        Mapping of state label → percentage share, rounded to two decimal
        places.  Values sum approximately to 100 (rounding may cause minor
        deviation).
    """
    if total_rows == 0:
        logger.warning("total_rows is 0 — all percentages will be 0.0")
        return {state: 0.0 for state in _SUPPORTED_STATES}

    percentages = {
        state: round(100.0 * count / total_rows, 2)
        for state, count in counts.items()
    }

    logger.debug("State percentages: %s", percentages)
    return percentages


def _get_dominant_state(counts: dict[str, int]) -> str:
    """Return the state label with the highest row count.

    If multiple states share the maximum count (extremely unlikely in
    practice), the one that appears first in ``_SUPPORTED_STATES`` wins,
    giving a deterministic result.

    Parameters
    ----------
    counts:
        Output of :func:`_get_state_counts`.

    Returns
    -------
    str
        Label of the dominant state.
    """
    if not any(counts.values()):
        logger.warning("All state counts are 0 — dominant_state defaulting to first supported state.")
        return _SUPPORTED_STATES[0]

    dominant = max(counts, key=lambda s: (counts[s], -_SUPPORTED_STATES.index(s)))
    logger.debug("Dominant state: %s (%d rows)", dominant, counts[dominant])
    return dominant


def _get_session_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-session summary table.

    For each unique ``session_id`` the table records:

    - ``dominant_state`` — the state that occurred most in that session.
    - ``{State}_pct`` columns for every state in ``_SUPPORTED_STATES``,
      giving the percentage share within that session.  Missing states are
      filled with ``0.0``.

    Parameters
    ----------
    df:
        Classified DataFrame containing ``session_id`` and ``state`` columns.

    Returns
    -------
    pandas.DataFrame
        One row per session.  Columns:
        ``session_id``, ``dominant_state``,
        plus one ``{State}_pct`` column per supported state.
    """
    logger.debug("Building session statistics for %d unique sessions …", df[_COL_SESSION].nunique())

    # Count rows per (session, state) pair
    grouped: pd.DataFrame = (
        df.groupby([_COL_SESSION, _COL_STATE])
        .size()
        .reset_index(name="count")
    )

    # Pivot so each state becomes its own column
    pivoted: pd.DataFrame = grouped.pivot_table(
        index=_COL_SESSION,
        columns=_COL_STATE,
        values="count",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure all supported states are present even if absent in this dataset
    for state in _SUPPORTED_STATES:
        if state not in pivoted.columns:
            pivoted[state] = 0

    # Session-level total rows for percentage calculation
    session_totals: pd.Series = pivoted[list(_SUPPORTED_STATES)].sum(axis=1)

    # Compute percentage columns
    pct_columns: dict[str, pd.Series] = {}
    for state in _SUPPORTED_STATES:
        col_name = f"{state}_pct"
        pct_columns[col_name] = (
            (pivoted[state] / session_totals * 100)
            .round(2)
            .fillna(0.0)
        )

    # Dominant state per session
    state_count_matrix = pivoted[list(_SUPPORTED_STATES)]
    dominant_series: pd.Series = state_count_matrix.idxmax(axis=1)

    # Assemble final table
    result = pd.DataFrame({_COL_SESSION: pivoted[_COL_SESSION]})
    result["dominant_state"] = dominant_series
    for col_name, series in pct_columns.items():
        result[col_name] = series

    logger.debug("Session statistics built — %d sessions, %d columns", len(result), len(result.columns))
    return result


def _get_aggressive_event_count(counts: dict[str, int]) -> int:
    """Calculate the total number of aggressive driving events.

    Aggressive events are defined as the combined count of *Acceleration*
    and *Deceleration* rows.  This metric is consumed downstream by
    driving-style analysis and vehicle health scoring.

    Parameters
    ----------
    counts:
        Output of :func:`_get_state_counts`.

    Returns
    -------
    int
        Total aggressive event count.
    """
    total = counts.get("Acceleration", 0) + counts.get("Deceleration", 0)
    logger.debug("Aggressive events: %d", total)
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_states(
    df: pd.DataFrame,
) -> tuple[StateAnalysisResult, StateAnalysisReport]:
    """Analyse a classified driving-state DataFrame and return dashboard-ready metrics.

    This is the primary entry point for the state analyzer.  It validates
    input, delegates to private helpers for each metric, and returns a fully
    populated :class:`StateAnalysisResult` alongside a
    :class:`StateAnalysisReport`.

    The input DataFrame is **never mutated**.

    Parameters
    ----------
    df:
        Fully classified OBD-II DataFrame produced by
        ``state_classifier.classify_states``.  Must contain at minimum
        the columns ``session_id`` and ``state``.

    Returns
    -------
    result : StateAnalysisResult
        Dashboard-ready metrics including state counts, percentages,
        per-session statistics, dominant state, and aggressive event count.
    report : StateAnalysisReport
        Lightweight summary suitable for logging and monitoring.

    Raises
    ------
    TypeError
        If *df* is not a :class:`pandas.DataFrame`.
    ValueError
        If *df* is empty or is missing required columns.

    Examples
    --------
    >>> result, report = analyze_states(df_classified)
    >>> report.log()
    >>> print(result.dominant_state)
    >>> print(result.session_statistics.head())
    """
    logger.info("Starting state analysis — %d input rows", len(df))

    # ------------------------------------------------------------------
    # 1. Validate — fail fast with a clear message
    # ------------------------------------------------------------------
    _validate_input(df)

    # ------------------------------------------------------------------
    # 2. Work on a view; no mutations to the caller's DataFrame
    # ------------------------------------------------------------------
    total_rows: int = len(df)

    # ------------------------------------------------------------------
    # 3. Compute aggregates
    # ------------------------------------------------------------------
    state_counts = _get_state_counts(df)
    state_percentages = _get_state_percentages(state_counts, total_rows)
    dominant_state = _get_dominant_state(state_counts)
    session_statistics = _get_session_statistics(df)
    aggressive_events = _get_aggressive_event_count(state_counts)

    # ------------------------------------------------------------------
    # 4. Assemble result
    # ------------------------------------------------------------------
    result = StateAnalysisResult(
        total_rows=total_rows,
        dominant_state=dominant_state,
        state_counts=state_counts,
        state_percentages=state_percentages,
        session_statistics=session_statistics,
        aggressive_events=aggressive_events,
    )

    # ------------------------------------------------------------------
    # 5. Assemble report
    # ------------------------------------------------------------------
    report = StateAnalysisReport(
        rows_analyzed=total_rows,
        session_count=df[_COL_SESSION].nunique(),
        dominant_state=dominant_state,
        aggressive_events=aggressive_events,
    )

    logger.info(
        "State analysis complete — %d rows | %d sessions | dominant: %s | aggressive events: %d",
        total_rows,
        report.session_count,
        dominant_state,
        aggressive_events,
    )

    return result, report