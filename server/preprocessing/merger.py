"""
merger.py
---------
AutoAssist – Phase 1: Data Foundation

Responsible for combining multiple cleaned, per-session OBD-II DataFrames into
a single master DataFrame suitable for fleet-level analysis and model training.

Each session receives a unique ``session_id`` column before concatenation, so
the origin of every row is always recoverable from the master DataFrame alone.
No information about session boundaries is lost.

This module does NOT load files, standardise columns, clean data, or engineer
features.
"""

import logging
from dataclasses import dataclass, field
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Name of the column injected into every session DataFrame before merging.
# Defined here so downstream modules can import the constant rather than
# hard-coding the string in multiple places.
SESSION_ID_COLUMN: Final[str] = "session_id"


# ---------------------------------------------------------------------------
# Merge report
# ---------------------------------------------------------------------------

@dataclass
class MergeReport:
    """Summary statistics produced by a single :func:`merge_sessions` call.

    Attributes:
        session_count:    Number of sessions successfully merged.
        total_rows:       Total row count in the master DataFrame.
        rows_per_session: Mapping of ``session_id → row count`` for every
                          session included in the merge.
        skipped_sessions: Session IDs that were rejected (e.g. empty
                          DataFrame) and excluded from the master.
        column_count:     Number of columns in the master DataFrame
                          (including ``session_id``).
    """
    session_count:    int            = 0
    total_rows:       int            = 0
    rows_per_session: dict[str, int] = field(default_factory=dict)
    skipped_sessions: list[str]      = field(default_factory=list)
    column_count:     int            = 0

    def log(self) -> None:
        """Emit a structured summary at INFO level."""
        logger.info(
            "Merge complete — sessions: %d | total rows: %d | columns: %d",
            self.session_count,
            self.total_rows,
            self.column_count,
        )
        if self.skipped_sessions:
            logger.warning(
                "Skipped %d empty/invalid session(s): %s",
                len(self.skipped_sessions),
                self.skipped_sessions,
            )
        for sid, count in self.rows_per_session.items():
            logger.debug("  session '%s': %d row(s)", sid, count)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_sessions(
    sessions: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, MergeReport]:
    """Merge multiple cleaned per-session DataFrames into one master DataFrame.

    Each session DataFrame is tagged with a ``session_id`` column before
    concatenation.  The master DataFrame therefore carries full provenance:
    any row can be traced back to its source session without consulting an
    external index.

    The ``session_id`` column is placed first so it is immediately visible
    when inspecting the master DataFrame.

    Args:
        sessions: A mapping of ``session_id → cleaned DataFrame``, as
                  produced by iterating over the output of
                  :func:`loader.load_csvs_from_directory` and passing each
                  DataFrame through the standardiser and cleaner.  The keys
                  become the ``session_id`` values in the master DataFrame.

    Returns:
        A tuple of:

        - **master** (:class:`pandas.DataFrame`) — the concatenated DataFrame
          with a contiguous integer index (``0 … N-1``) and a leading
          ``session_id`` column.
        - **report** (:class:`MergeReport`) — summary statistics for the
          merge operation.

    Raises:
        TypeError:  If ``sessions`` is not a ``dict``, or if any value in
                    the dict is not a :class:`pandas.DataFrame`.
        ValueError: If ``sessions`` is empty, or if every session was skipped
                    (nothing left to merge).

    Notes:
        - The original DataFrames are **not** mutated; each receives a
          shallow copy before the ``session_id`` column is added.
        - Sessions whose DataFrame is empty are skipped and recorded in
          :attr:`MergeReport.skipped_sessions`.
        - Column sets do not have to be identical across sessions.
          ``pd.concat`` with ``join="outer"`` fills missing columns with
          ``NaN``, which is preferable to silently discarding data.  A
          warning is emitted when column sets differ.
    """
    _validate_input(sessions)

    report   = MergeReport()
    tagged: list[pd.DataFrame] = []
    all_column_sets: list[frozenset[str]] = []

    for session_id, df in sessions.items():
        if df.empty:
            logger.warning("Session '%s' is empty — skipping.", session_id)
            report.skipped_sessions.append(session_id)
            continue

        tagged_df = _tag_session(df, session_id)
        row_count = len(tagged_df)

        report.rows_per_session[session_id] = row_count
        all_column_sets.append(frozenset(tagged_df.columns))
        tagged.append(tagged_df)

        logger.debug("Queued session '%s': %d row(s).", session_id, row_count)

    if not tagged:
        raise ValueError(
            "No sessions remained after skipping empty/invalid DataFrames. "
            "Verify that cleaner.py ran successfully on all sessions."
        )

    _warn_on_column_mismatch(all_column_sets, list(sessions.keys()))

    master = pd.concat(tagged, axis=0, join="outer", ignore_index=True)
    master = _move_session_id_first(master)

    report.session_count = len(tagged)
    report.total_rows    = len(master)
    report.column_count  = len(master.columns)
    report.log()

    return master, report


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _validate_input(sessions: dict[str, pd.DataFrame]) -> None:
    """Raise on bad input before any merge work begins.

    Args:
        sessions: Candidate input to :func:`merge_sessions`.

    Raises:
        TypeError:  ``sessions`` is not a dict, or contains non-DataFrame
                    values.
        ValueError: ``sessions`` is empty.
    """
    if not isinstance(sessions, dict):
        raise TypeError(
            f"'sessions' must be a dict, got {type(sessions).__name__!r}."
        )
    if not sessions:
        raise ValueError(
            "'sessions' is empty. Pass at least one session DataFrame."
        )

    non_df = {
        k: type(v).__name__
        for k, v in sessions.items()
        if not isinstance(v, pd.DataFrame)
    }
    if non_df:
        raise TypeError(
            f"All values in 'sessions' must be DataFrames. "
            f"Non-DataFrame entries: {non_df}"
        )


def _tag_session(df: pd.DataFrame, session_id: str) -> pd.DataFrame:
    """Return a shallow copy of *df* with a ``session_id`` column added.

    A shallow copy is used so the caller's DataFrame is never mutated, while
    avoiding a full deep copy of potentially large telemetry arrays.

    The ``session_id`` column is a Categorical dtype backed by a single
    repeated string value.  This avoids storing the same string N times as
    a plain ``object`` column and reduces memory usage for large sessions.

    Args:
        df:         Cleaned session DataFrame.
        session_id: Identifier string for this session (typically the file
                    stem from the loader, e.g. ``"trip_001"``).

    Returns:
        Copy of *df* with ``session_id`` as a Categorical column.
    """
    tagged = df.copy(deep=False)
    tagged[SESSION_ID_COLUMN] = pd.Categorical([session_id] * len(tagged))
    return tagged


def _move_session_id_first(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns so ``session_id`` is the first (leftmost) column.

    Placing the provenance column first makes it immediately visible when
    calling ``df.head()`` or exporting to CSV, without requiring the reader
    to search the column list.

    Args:
        df: Master DataFrame with ``session_id`` in an arbitrary position.

    Returns:
        The same DataFrame with columns reordered.
    """
    cols = [SESSION_ID_COLUMN] + [c for c in df.columns if c != SESSION_ID_COLUMN]
    return df[cols]


def _warn_on_column_mismatch(
    column_sets: list[frozenset[str]],
    session_ids: list[str],
) -> None:
    """Log a warning if sessions do not share an identical column set.

    Column mismatches are not fatal — ``pd.concat`` with ``join="outer"``
    handles them by filling absent columns with ``NaN``.  However, a mismatch
    is worth surfacing because it may indicate a schema version difference
    between sessions (e.g. a new PID added mid-dataset) that downstream
    modules should be aware of.

    Args:
        column_sets: One frozenset of column names per session, in the same
                     order as ``session_ids``.
        session_ids: Session identifiers corresponding to each column set.
    """
    if not column_sets:
        return

    reference = column_sets[0]
    mismatched = [
        sid
        for sid, cols in zip(session_ids, column_sets)
        if cols != reference
    ]

    if mismatched:
        logger.warning(
            "Column set differs across sessions. "
            "Missing columns will be filled with NaN. "
            "Sessions with non-standard columns: %s",
            mismatched,
        )