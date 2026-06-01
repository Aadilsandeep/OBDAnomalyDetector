"""
loader.py
---------
AutoAssist – Phase 1: Data Foundation

Responsible for loading OBD-II telemetry CSV files into pandas DataFrames.
Handles single-file and batch (directory) loading with robust error handling.
"""

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Single-file loader
# ---------------------------------------------------------------------------

def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Load a single CSV file into a pandas DataFrame.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        A DataFrame containing the parsed CSV content.

    Raises:
        FileNotFoundError: If the path does not exist or is not a file.
        ValueError: If the file is empty or cannot be parsed as valid CSV.
        OSError: If the file cannot be opened due to a permission or I/O error.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: '{path}'")

    if not path.is_file():
        raise FileNotFoundError(f"Path exists but is not a file: '{path}'")

    if path.stat().st_size == 0:
        raise ValueError(f"CSV file is empty: '{path}'")

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        # Covers files that contain only whitespace / no columns
        raise ValueError(f"CSV file has no parseable content: '{path}'")
    except pd.errors.ParserError as exc:
        raise ValueError(f"CSV parsing failed for '{path}': {exc}") from exc
    except OSError as exc:
        raise OSError(f"Could not open '{path}': {exc}") from exc

    if df.empty:
        raise ValueError(
            f"CSV file parsed successfully but contains no rows: '{path}'"
        )

    logger.debug("Loaded '%s' — %d rows × %d columns", path.name, *df.shape)
    return df


# ---------------------------------------------------------------------------
# Batch (directory) loader
# ---------------------------------------------------------------------------

def load_csvs_from_directory(
    directory: str | Path,
    *,
    recursive: bool = False,
    skip_errors: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load all CSV files found in a directory into a dictionary of DataFrames.

    Each entry in the returned mapping uses the file's stem (filename without
    extension) as the key, making downstream merging and identification simple.

    Args:
        directory:   Path to the directory that contains the CSV files.
        recursive:   If True, scan subdirectories as well as the top-level
                     directory. Defaults to False.
        skip_errors: If True, files that raise an error are logged and skipped
                     rather than aborting the entire batch. Defaults to False,
                     which surfaces the first error immediately.

    Returns:
        An ordered dict mapping ``file_stem -> DataFrame`` for every CSV that
        loaded successfully.  The dict is sorted by key for deterministic
        ordering across runs.

    Raises:
        NotADirectoryError: If ``directory`` does not exist or is not a
                            directory.
        ValueError:         If no CSV files are found in the directory (or its
                            subdirectories when ``recursive=True``).
        Any exception raised by :func:`load_csv` when ``skip_errors=False``.
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise NotADirectoryError(f"Directory not found: '{dir_path}'")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"Path exists but is not a directory: '{dir_path}'")

    glob_pattern = "**/*.csv" if recursive else "*.csv"
    csv_files: list[Path] = sorted(dir_path.glob(glob_pattern))

    if not csv_files:
        raise ValueError(
            f"No CSV files found in '{dir_path}'"
            + (" (including subdirectories)" if recursive else "")
        )

    logger.info(
        "Found %d CSV file(s) in '%s'%s",
        len(csv_files),
        dir_path,
        " (recursive)" if recursive else "",
    )

    results: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    for csv_path in csv_files:
        key = csv_path.stem  # e.g. "trip_001" from "trip_001.csv"

        try:
            results[key] = load_csv(csv_path)
        except (FileNotFoundError, ValueError, OSError) as exc:
            if skip_errors:
                logger.warning("Skipping '%s': %s", csv_path.name, exc)
                errors[str(csv_path)] = str(exc)
            else:
                raise

    if errors:
        logger.warning(
            "Completed with %d skipped file(s): %s",
            len(errors),
            list(errors.keys()),
        )

    logger.info(
        "Successfully loaded %d / %d file(s).",
        len(results),
        len(csv_files),
    )

    return dict(sorted(results.items()))