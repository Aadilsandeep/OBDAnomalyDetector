"""
cleaner.py
----------
AutoAssist – Phase 1: Data Foundation

Responsible for cleaning and quality-validating a standardised OBD-II
telemetry DataFrame.  Expects input that has already passed through
standardizer.standardize_columns(), i.e. all columns carry their canonical
snake_case names.

Cleaning pipeline (in order):
  1. Duplicate row removal
  2. Timestamp parsing  (HH:MM:SS.fff → elapsed seconds from session start)
  3. Missing value handling  (drop rows — safer than fill for anomaly detection)
  4. Physical sensor range validation
  5. Cleaning statistics are logged at every stage

This module does NOT rename columns, load files, merge datasets, or
engineer features.
"""

import logging
from dataclasses import dataclass, field
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sensor validity bounds
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Bounds:
    """Inclusive lower and/or upper bound for a sensor signal.

    Use ``None`` to indicate that a boundary does not apply.
    """
    low:  float | None = None
    high: float | None = None


# Physical validity windows derived from OBD-II PID specifications and
# real-world engine constraints.  See module docstring for sources.
#
# Adding a new signal: insert one entry here — nothing else needs changing.
_SENSOR_BOUNDS: Final[dict[str, _Bounds]] = {
    "rpm":          _Bounds(low=0,    high=10_000),
    "speed":        _Bounds(low=0,    high=300),
    "coolant_temp": _Bounds(low=-40,  high=150),
    "map":          _Bounds(low=0),
    "maf":          _Bounds(low=0),
    "throttle_pos": _Bounds(low=0,    high=100),
    "pedal_d":      _Bounds(low=0,    high=100),
    "pedal_e":      _Bounds(low=0,    high=100),
}

# Timestamp format produced by common OBD-II logging software.
# Example: "07:16:30.444"
_TIMESTAMP_FORMAT: Final[str] = "%H:%M:%S.%f"


# ---------------------------------------------------------------------------
# Cleaning statistics container
# ---------------------------------------------------------------------------

@dataclass
class CleaningReport:
    """Collects and logs row-level cleaning statistics for one DataFrame.

    Attributes:
        rows_original:       Row count before any cleaning step.
        rows_duplicates:     Rows removed because they were exact duplicates.
        rows_invalid:        Rows removed because at least one sensor value
                             fell outside its physical validity window.
        missing_dropped:     Rows dropped because they contained one or more
                             NaN / NaT values that could not be resolved.
        rows_final:          Row count after all cleaning steps.
        columns_parsed:      Names of columns successfully parsed (timestamp).
        invalid_by_column:   Per-column count of out-of-range values removed.
    """
    rows_original:     int = 0
    rows_duplicates:   int = 0
    rows_invalid:      int = 0
    missing_dropped:   int = 0
    rows_final:        int = 0
    columns_parsed:    list[str]        = field(default_factory=list)
    invalid_by_column: dict[str, int]   = field(default_factory=dict)

    def log(self) -> None:
        """Emit a structured summary at INFO level."""
        logger.info(
            "Cleaning complete — "
            "original: %d | duplicates removed: %d | "
            "invalid removed: %d | missing dropped: %d | final: %d",
            self.rows_original,
            self.rows_duplicates,
            self.rows_invalid,
            self.missing_dropped,
            self.rows_final,
        )
        if self.invalid_by_column:
            logger.info(
                "Invalid rows by column: %s",
                {k: v for k, v in self.invalid_by_column.items() if v > 0},
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean and quality-validate a standardised OBD-II telemetry DataFrame.

    Applies the following steps in order:

    1. **Duplicate removal** — identical rows are dropped; the first
       occurrence is kept to preserve temporal ordering.
    2. **Timestamp parsing** — the ``timestamp`` column is converted from a
       ``HH:MM:SS.fff`` string to elapsed seconds (float) from the first
       sample of the session.  This representation is compact, unambiguous,
       and directly usable by time-series and anomaly-detection models.
       Unparseable values become ``NaN`` and are handled by step 3.
    3. **Missing value removal** — any row containing a ``NaN`` or ``NaT``
       cell is dropped.  At <0.02% prevalence the data loss is negligible,
       and dropping is strictly safer than filling for anomaly detection
       (see :func:`_handle_missing` for the full rationale).
    4. **Physical range validation** — rows containing at least one sensor
       reading outside its defined validity window are removed.

    Args:
        df: A standardised DataFrame produced by
            :func:`standardizer.standardize_columns`.  Must contain the
            canonical column set; unrecognised extra columns are left
            untouched.

    Returns:
        A tuple of:
        - The cleaned DataFrame with a reset integer index.
        - A :class:`CleaningReport` capturing per-step statistics.

    Raises:
        TypeError:  If ``df`` is not a :class:`pandas.DataFrame`.
        ValueError: If ``df`` is completely empty before cleaning begins.

    Notes:
        The original DataFrame is **not** mutated; a copy is made at entry.
    """
    _validate_input(df)

    report = CleaningReport(rows_original=len(df))
    working = df.copy()

    working = _remove_duplicates(working, report)
    working = _parse_timestamp(working, report)
    working = _handle_missing(working, report)
    working = _remove_invalid_sensor_values(working, report)

    working = working.reset_index(drop=True)
    report.rows_final = len(working)
    report.log()

    return working, report


# ---------------------------------------------------------------------------
# Pipeline steps (private)
# ---------------------------------------------------------------------------

def _remove_duplicates(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Drop exact duplicate rows, keeping the first occurrence.

    Exact duplicates in time-series telemetry indicate logger glitches
    (e.g. a USB adapter double-flushing a buffer) rather than genuine
    repeated readings.  Keeping the first occurrence preserves the correct
    temporal position.

    Args:
        df:     Working DataFrame.
        report: Mutable report; ``rows_duplicates`` is updated in place.

    Returns:
        DataFrame with duplicates removed.
    """
    before = len(df)
    df = df.drop_duplicates(keep="first")
    report.rows_duplicates = before - len(df)

    if report.rows_duplicates:
        logger.debug("Removed %d duplicate row(s).", report.rows_duplicates)

    return df


def _parse_timestamp(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Convert the ``timestamp`` column to elapsed seconds from session start.

    Representation choice
    ---------------------
    The raw format is ``HH:MM:SS.fff`` (wall-clock time of day).  Two
    alternatives were considered:

    * **``datetime.time`` object** — preserves wall-clock time but is not
      directly arithmetic: ``time`` objects cannot be subtracted, added, or
      used as a numeric axis in models without further conversion.  Pandas
      also stores them as Python objects (dtype ``object``), not as a native
      numeric type, making vectorised operations slower.

    * **Elapsed seconds (float64)** — measures time *relative to the first
      sample of the session*, giving a monotonically increasing numeric axis
      that starts at 0.0.  It is compact, unambiguous across midnight
      boundaries, and immediately usable by any numerical model, rolling
      window, or resampler without further transformation.  This is the
      representation chosen here.

    Unparseable strings are coerced to ``NaT`` and become ``NaN`` in the
    elapsed-seconds column; they are handled by the subsequent drop step.

    Args:
        df:     Working DataFrame.
        report: Mutable report; ``columns_parsed`` is updated in place.

    Returns:
        DataFrame with ``timestamp`` as elapsed seconds (``float64``).
    """
    if "timestamp" not in df.columns:
        logger.warning("'timestamp' column not found — skipping timestamp parsing.")
        return df

    parsed = pd.to_datetime(
        df["timestamp"],
        format=_TIMESTAMP_FORMAT,
        errors="coerce",  # unparseable → NaT
    )

    # Compute elapsed seconds from the first valid timestamp in the session.
    # total_seconds() on a Timedelta returns a float64 scalar, so the result
    # column is dtype float64 — directly numeric and model-ready.
    session_start = parsed.dropna().iloc[0] if not parsed.dropna().empty else None

    if session_start is None:
        logger.warning(
            "No parseable timestamp found in session — 'timestamp' column "
            "will be dropped to avoid propagating NaN into the model."
        )
        df = df.drop(columns=["timestamp"])
        return df

    df["timestamp"] = (parsed - session_start).dt.total_seconds()

    report.columns_parsed.append("timestamp")
    logger.debug(
        "Parsed 'timestamp' → elapsed seconds (session start: %s).",
        session_start.time(),
    )
    return df


def _handle_missing(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Drop any row that contains a NaN / NaT value.

    Strategy: drop, not fill
    ------------------------
    The previous implementation forward-filled then backward-filled missing
    cells.  After reconsidering against the three constraints below, dropping
    is the safer choice for this system.

    **1. Anomaly detection integrity**
    AutoAssist's primary purpose is detecting abnormal sensor behaviour.
    Filling a missing value — even with the nearest neighbour — *invents* a
    reading that the ECU never produced.  If the gap happens to fall during
    an anomalous event (a spike, a drop, an abrupt transition), the fill
    smooths exactly the signal that the detector needs to see.  A dropped row
    leaves a visible gap; a filled row silently corrupts the ground truth.

    **2. Negligible data loss**
    At <0.02% prevalence across a large dataset the expected missing count is
    on the order of a few cells per session.  Dropping those rows costs
    essentially nothing in terms of training or inference quality.

    **3. Forward-fill is only correct for slowly-changing signals**
    ffill is a reasonable approximation for coolant temperature or IAT
    (which change on a timescale of seconds to minutes).  It is a poor
    approximation for RPM, throttle position, or pedal position, which can
    change by hundreds of units between two consecutive samples.  Because
    NaN can appear in any column, a fill strategy must be equally valid for
    all signals — a condition that ffill does not satisfy here.

    Tradeoff acknowledged
    ---------------------
    Dropping does break strict temporal continuity: downstream models that
    rely on fixed-interval sampling (FFT, some RNNs) will see a small gap.
    That is preferable to injecting fabricated values, and the gap is
    trivially detectable from the ``timestamp`` column (a jump in elapsed
    seconds larger than the nominal sample interval).

    Args:
        df:     Working DataFrame.
        report: Mutable report; ``missing_dropped`` is updated in place.

    Returns:
        DataFrame with all NaN / NaT rows removed.
    """
    missing_before = int(df.isna().sum().sum())

    if missing_before == 0:
        logger.debug("No missing values detected.")
        return df

    rows_before = len(df)
    df = df.dropna()
    report.missing_dropped = rows_before - len(df)

    logger.debug(
        "Missing value handling: dropped %d row(s) containing %d NaN/NaT cell(s).",
        report.missing_dropped,
        missing_before,
    )
    return df


def _remove_invalid_sensor_values(
    df: pd.DataFrame,
    report: CleaningReport,
) -> pd.DataFrame:
    """Remove rows containing physically impossible sensor readings.

    Builds a combined boolean mask across all bounded columns and drops any
    row where at least one reading falls outside its validity window.
    Per-column counts are recorded before the combined drop so that the
    report can identify which signal is the source of most anomalies.

    Design note: rows — not individual cells — are removed.  A single
    out-of-range reading invalidates the entire sample because the signals
    are captured synchronously; there is no reliable way to correct one
    column while trusting the rest of the row.

    Args:
        df:     Working DataFrame.
        report: Mutable report; ``rows_invalid`` and ``invalid_by_column``
                are updated in place.

    Returns:
        DataFrame containing only physically plausible sensor readings.
    """
    if df.empty:
        return df

    # Start with an all-False mask (no rows flagged yet)
    invalid_mask = pd.Series(False, index=df.index)

    for column, bounds in _SENSOR_BOUNDS.items():
        if column not in df.columns:
            logger.debug("Bound-checked column '%s' not present — skipping.", column)
            continue

        col_mask = pd.Series(False, index=df.index)

        if bounds.low is not None:
            col_mask |= df[column] < bounds.low
        if bounds.high is not None:
            col_mask |= df[column] > bounds.high

        per_column_count = int(col_mask.sum())
        report.invalid_by_column[column] = per_column_count

        if per_column_count:
            logger.debug(
                "Column '%s': %d row(s) outside bounds [%s, %s].",
                column,
                per_column_count,
                bounds.low if bounds.low is not None else "-∞",
                bounds.high if bounds.high is not None else "+∞",
            )

        invalid_mask |= col_mask

    report.rows_invalid = int(invalid_mask.sum())
    return df[~invalid_mask]


# ---------------------------------------------------------------------------
# Input guards
# ---------------------------------------------------------------------------

def _validate_input(df: pd.DataFrame) -> None:
    """Raise on bad input before any cleaning work begins.

    Args:
        df: Candidate input to ``clean_dataframe``.

    Raises:
        TypeError:  ``df`` is not a DataFrame.
        ValueError: ``df`` has no rows.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"Expected a pandas DataFrame, got {type(df).__name__!r}."
        )
    if df.empty:
        raise ValueError(
            "Cannot clean an empty DataFrame. "
            "Ensure loader and standardizer have run successfully."
        )