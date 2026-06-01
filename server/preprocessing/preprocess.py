"""
preprocess.py
-------------
AutoAssist – Phase 1: Data Foundation

Pipeline orchestrator.  Drives the full preprocessing sequence for every
OBD-II session CSV in ``data/raw`` and produces:

  * One cleaned CSV per session in ``data/processed/``
  * A single ``data/processed/master_dataset.csv`` containing all sessions
  * A :class:`PreprocessingReport` with fleet-level statistics

Pipeline order per session
--------------------------
  load → standardize → clean → save individual CSV

After all sessions
------------------
  merge → save master CSV → return (master DataFrame, report)

This module does NOT implement loading, standardising, cleaning, or merging
logic — it delegates to the four specialised modules and only owns the
coordination between them.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pandas as pd

from . import cleaner, loader, merger, standardizer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

# These defaults are relative to the repository root.  Both can be overridden
# by passing explicit arguments to run_preprocessing() for testing or
# alternative deployment layouts.
DEFAULT_RAW_DIR:       Final[Path] = Path("data/raw")
DEFAULT_PROCESSED_DIR: Final[Path] = Path("data/processed")

# Name of the fleet-wide output file placed in DEFAULT_PROCESSED_DIR.
MASTER_FILENAME: Final[str] = "master_dataset.csv"


# ---------------------------------------------------------------------------
# Preprocessing report
# ---------------------------------------------------------------------------

@dataclass
class PreprocessingReport:
    """Fleet-level statistics aggregated across all per-session pipeline runs.

    Every numeric field is the sum across all sessions that were processed
    successfully.  Sessions that failed are counted separately in
    ``failed_sessions`` and excluded from all numeric totals.

    Attributes:
        files_found:        Number of CSV files discovered in the raw directory.
        files_processed:    Number of sessions that completed the full pipeline
                            without raising an unhandled exception.
        files_failed:       Number of sessions that raised an exception during
                            load, standardise, or clean.
        total_rows_before:  Sum of ``CleaningReport.rows_original`` across all
                            successful sessions (rows entering the cleaner).
        total_rows_after:   Sum of ``CleaningReport.rows_final`` across all
                            successful sessions (rows exiting the cleaner).
        total_duplicates:   Sum of ``CleaningReport.rows_duplicates`` across
                            all successful sessions.
        total_invalid:      Sum of ``CleaningReport.rows_invalid`` across all
                            successful sessions.
        total_missing:      Sum of ``CleaningReport.missing_dropped`` across
                            all successful sessions.
        failed_sessions:    Mapping of ``session_id → error message`` for
                            every session that could not be processed.
        master_path:        Absolute path to the saved master CSV, or ``None``
                            if saving was skipped or failed.
    """
    files_found:       int               = 0
    files_processed:   int               = 0
    files_failed:      int               = 0
    total_rows_before: int               = 0
    total_rows_after:  int               = 0
    total_duplicates:  int               = 0
    total_invalid:     int               = 0
    total_missing:     int               = 0
    failed_sessions:   dict[str, str]    = field(default_factory=dict)
    master_path:       Path | None       = None

    @property
    def total_rows_removed(self) -> int:
        """Total rows removed across all cleaning steps."""
        return self.total_rows_before - self.total_rows_after

    @property
    def retention_rate(self) -> float:
        """Fraction of rows retained after cleaning (0.0 – 1.0).

        Returns 0.0 if no rows were seen (empty dataset).
        """
        if self.total_rows_before == 0:
            return 0.0
        return self.total_rows_after / self.total_rows_before

    def log(self) -> None:
        """Emit the full fleet-level summary at INFO level."""
        logger.info(
            "Preprocessing complete — "
            "files found: %d | processed: %d | failed: %d",
            self.files_found,
            self.files_processed,
            self.files_failed,
        )
        logger.info(
            "Rows — before: %d | after: %d | removed: %d | "
            "retention: %.2f%%",
            self.total_rows_before,
            self.total_rows_after,
            self.total_rows_removed,
            self.retention_rate * 100,
        )
        logger.info(
            "Removed breakdown — duplicates: %d | invalid: %d | missing: %d",
            self.total_duplicates,
            self.total_invalid,
            self.total_missing,
        )
        if self.master_path:
            logger.info("Master dataset saved to: %s", self.master_path)
        if self.failed_sessions:
            logger.warning(
                "%d session(s) failed and were excluded from the master:\n%s",
                len(self.failed_sessions),
                "\n".join(
                    f"  • {sid}: {err}"
                    for sid, err in self.failed_sessions.items()
                ),
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_preprocessing(
    raw_dir:       str | Path = DEFAULT_RAW_DIR,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
    *,
    skip_errors:   bool = True,
) -> tuple[pd.DataFrame, PreprocessingReport]:
    """Run the full AutoAssist Phase 1 preprocessing pipeline.

    For each CSV file in *raw_dir* the pipeline executes in order:

    1. **Load** — read the CSV into a DataFrame
       (:func:`loader.load_csv`).
    2. **Standardise** — rename raw OBD-II headers to canonical names
       (:func:`standardizer.standardize_columns`).
    3. **Clean** — remove duplicates, parse timestamps, drop missing rows,
       and remove physically invalid readings
       (:func:`cleaner.clean_dataframe`).
    4. **Save individual session** — write the cleaned DataFrame to
       *processed_dir/<session_id>.csv*.

    After all sessions are processed:

    5. **Merge** — concatenate all cleaned sessions into one master DataFrame
       with a ``session_id`` provenance column
       (:func:`merger.merge_sessions`).
    6. **Save master** — write to *processed_dir/master_dataset.csv*.

    Args:
        raw_dir:       Directory containing the raw OBD-II CSV files.
                       Defaults to ``data/raw``.
        processed_dir: Directory where cleaned session CSVs and the master
                       dataset are written.  Created if it does not exist.
                       Defaults to ``data/processed``.
        skip_errors:   If ``True`` (default), a session that raises an
                       exception during load / standardise / clean is logged,
                       recorded in the report, and skipped — the pipeline
                       continues with the remaining sessions.
                       If ``False``, the first error is re-raised immediately,
                       aborting the entire run.  Useful for CI or strict
                       data-validation workflows.

    Returns:
        A tuple of:

        - **master** (:class:`pandas.DataFrame`) — the merged, cleaned
          dataset with a leading ``session_id`` column.
        - **report** (:class:`PreprocessingReport`) — fleet-level statistics
          aggregated across all sessions.

    Raises:
        NotADirectoryError: If *raw_dir* does not exist or is not a directory.
        ValueError:         If no CSV files are found in *raw_dir*, or if
                            every session failed and no data remains to merge.
        Any exception raised by a pipeline stage when ``skip_errors=False``.
    """
    raw_dir       = Path(raw_dir)
    processed_dir = Path(processed_dir)

    _validate_directories(raw_dir, processed_dir)

    report = PreprocessingReport()

    # ------------------------------------------------------------------
    # Phase A: per-session pipeline
    # ------------------------------------------------------------------
    raw_dataframes = _load_raw_sessions(raw_dir, report)
    cleaned_sessions = _process_sessions(
        raw_dataframes, processed_dir, report, skip_errors=skip_errors
    )

    if not cleaned_sessions:
        raise ValueError(
            "No sessions were cleaned successfully. "
            "Check the log for per-session errors."
        )

    # ------------------------------------------------------------------
    # Phase B: merge and save master
    # ------------------------------------------------------------------
    master, _ = merger.merge_sessions(cleaned_sessions)
    report.master_path = _save_master(master, processed_dir)

    report.log()
    return master, report


# ---------------------------------------------------------------------------
# Private — directory & I/O helpers
# ---------------------------------------------------------------------------

def _validate_directories(raw_dir: Path, processed_dir: Path) -> None:
    """Raise early if *raw_dir* is unusable.

    *processed_dir* is created if absent rather than raising, because an
    absent output directory is a recoverable situation.

    Args:
        raw_dir:       Source directory to validate.
        processed_dir: Destination directory; created if missing.

    Raises:
        NotADirectoryError: If *raw_dir* does not exist or is not a directory.
    """
    if not raw_dir.exists() or not raw_dir.is_dir():
        raise NotADirectoryError(
            f"Raw data directory not found or is not a directory: '{raw_dir}'"
        )

    processed_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory ready: '%s'", processed_dir)


def _load_raw_sessions(
    raw_dir: Path,
    report:  PreprocessingReport,
) -> dict[str, pd.DataFrame]:
    """Discover and load all CSV files from *raw_dir*.

    Delegates to :func:`loader.load_csvs_from_directory` which returns a
    ``dict[str, DataFrame]`` keyed by file stem.  The file count is recorded
    in *report* before any per-session processing begins.

    Args:
        raw_dir: Directory to scan for CSV files.
        report:  Mutable report; ``files_found`` is updated here.

    Returns:
        Mapping of ``session_id → raw DataFrame``.

    Raises:
        ValueError: If the directory contains no CSV files (propagated from
                    the loader).
    """
    raw_sessions = loader.load_csvs_from_directory(raw_dir, skip_errors=False)
    report.files_found = len(raw_sessions)
    logger.info("Discovered %d CSV file(s) in '%s'.", report.files_found, raw_dir)
    return raw_sessions


def _process_sessions(
    raw_sessions:  dict[str, pd.DataFrame],
    processed_dir: Path,
    report:        PreprocessingReport,
    *,
    skip_errors:   bool,
) -> dict[str, pd.DataFrame]:
    """Run standardise → clean → save for every raw session DataFrame.

    Each session is processed independently.  On success the cleaned DataFrame
    is written to *processed_dir* and its :class:`~cleaner.CleaningReport`
    statistics are accumulated into *report*.  On failure the session is
    either skipped (``skip_errors=True``) or re-raised (``skip_errors=False``).

    Args:
        raw_sessions:  Mapping of ``session_id → raw DataFrame`` from the
                       loader.
        processed_dir: Destination for per-session cleaned CSVs.
        report:        Mutable fleet-level report updated after each session.
        skip_errors:   Controls error propagation (see :func:`run_preprocessing`).

    Returns:
        Mapping of ``session_id → cleaned DataFrame`` for every session that
        completed the pipeline successfully.
    """
    cleaned: dict[str, pd.DataFrame] = {}

    for session_id, raw_df in raw_sessions.items():
        logger.info("Processing session '%s' (%d rows)...", session_id, len(raw_df))

        try:
            std_df              = standardizer.standardize_columns(raw_df)
            clean_df, clean_rpt = cleaner.clean_dataframe(std_df)

            _accumulate_cleaning_stats(report, clean_rpt)
            _save_session(clean_df, session_id, processed_dir)

            cleaned[session_id] = clean_df
            report.files_processed += 1

        except Exception as exc:
            _handle_session_error(session_id, exc, report, skip_errors)

    return cleaned


def _accumulate_cleaning_stats(
    report:    PreprocessingReport,
    clean_rpt: cleaner.CleaningReport,
) -> None:
    """Add one session's :class:`~cleaner.CleaningReport` into the fleet totals.

    Args:
        report:    Fleet-level report being built across all sessions.
        clean_rpt: Per-session report produced by :func:`cleaner.clean_dataframe`.
    """
    report.total_rows_before += clean_rpt.rows_original
    report.total_rows_after  += clean_rpt.rows_final
    report.total_duplicates  += clean_rpt.rows_duplicates
    report.total_invalid     += clean_rpt.rows_invalid
    report.total_missing     += clean_rpt.missing_dropped


def _save_session(
    df:            pd.DataFrame,
    session_id:    str,
    processed_dir: Path,
) -> None:
    """Write a cleaned session DataFrame to *processed_dir/<session_id>.csv*.

    The file is written without the pandas integer index — the index carries
    no information at this stage and wastes a column in every CSV.

    Args:
        df:            Cleaned session DataFrame.
        session_id:    Used as the output filename stem.
        processed_dir: Destination directory (must already exist).

    Raises:
        OSError: If the file cannot be written (propagates to the caller).
    """
    output_path = processed_dir / f"{session_id}.csv"
    df.to_csv(output_path, index=False)
    logger.debug("Saved cleaned session to '%s'.", output_path)


def _save_master(master: pd.DataFrame, processed_dir: Path) -> Path:
    """Write the merged master DataFrame to *processed_dir/master_dataset.csv*.

    Args:
        master:        The merged, fleet-wide DataFrame.
        processed_dir: Destination directory.

    Returns:
        Absolute path of the saved file.

    Raises:
        OSError: If the file cannot be written.
    """
    master_path = processed_dir / MASTER_FILENAME
    master.to_csv(master_path, index=False)
    logger.info(
        "Master dataset saved — %d rows × %d columns → '%s'.",
        len(master),
        len(master.columns),
        master_path,
    )
    return master_path.resolve()


def _handle_session_error(
    session_id:  str,
    exc:         Exception,
    report:      PreprocessingReport,
    skip_errors: bool,
) -> None:
    """Record a failed session and either continue or re-raise.

    Args:
        session_id:  Identifier of the session that failed.
        exc:         The exception that was raised.
        report:      Fleet-level report; ``files_failed`` and
                     ``failed_sessions`` are updated.
        skip_errors: If ``True``, log and continue.  If ``False``, re-raise.

    Raises:
        Exception: The original exception, when ``skip_errors=False``.
    """
    report.files_failed += 1
    report.failed_sessions[session_id] = f"{type(exc).__name__}: {exc}"

    if skip_errors:
        logger.warning(
            "Session '%s' failed and was skipped: %s: %s",
            session_id,
            type(exc).__name__,
            exc,
        )
    else:
        logger.error(
            "Session '%s' failed (skip_errors=False — aborting): %s",
            session_id,
            exc,
        )
        raise