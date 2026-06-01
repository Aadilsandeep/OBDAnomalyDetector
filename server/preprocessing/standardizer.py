"""
standardizer.py
---------------
AutoAssist – Phase 1: Data Foundation

Responsible for normalising raw OBD-II column names into a canonical internal
schema.  Every module downstream (cleaner, merger, feature engineering) works
exclusively with the standardised names, so the rest of the pipeline is fully
decoupled from whatever header strings a data source happens to produce.

Encoding variants
-----------------
OBD-II logger software often writes the degree symbol (U+00B0) through
different encodings that survive into the CSV header as different byte
sequences, most commonly:

  Correct UTF-8   →  °   (U+00B0, one byte: 0xC2 0xB0)
  Latin-1 mojibake→  Â°  (U+00C2 U+00B0 — UTF-8 bytes read as Latin-1)

To handle this without duplicating the schema, the module defines the
canonical schema once (using the correct UTF-8 symbol) and resolves all
known encoding variants to that symbol *before* any column lookup occurs.
"""

import logging
import re
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encoding normalisation
# ---------------------------------------------------------------------------

# Each entry maps a mis-encoded string fragment to its correct UTF-8 form.
# Add new variants here if additional encoding artefacts are discovered in
# the wild — no other part of the module needs to change.
_ENCODING_VARIANTS: Final[dict[str, str]] = {
    "Â°": "°",   # UTF-8 degree sign mis-read as Latin-1 (most common)
    "â„ƒ": "°C", # Full Celsius sequence mangled by double-encoding (rare)
}

# Pre-compile a single regex that matches any variant in one pass.
# re.escape ensures special characters in keys are treated as literals.
_VARIANT_RE: Final[re.Pattern[str]] = re.compile(
    "|".join(re.escape(bad) for bad in _ENCODING_VARIANTS)
)


def _normalize_encoding(text: str) -> str:
    """Replace all known encoding artefacts in *text* with correct UTF-8.

    Applies every substitution in :data:`_ENCODING_VARIANTS` using a single
    compiled regex pass, so cost is O(n) in string length regardless of how
    many variants are registered.

    Args:
        text: A raw column header string from the CSV file.

    Returns:
        The header string with all known encoding artefacts corrected.
    """
    return _VARIANT_RE.sub(lambda m: _ENCODING_VARIANTS[m.group()], text)


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a shallow copy of *df* with encoding-normalised column names.

    The DataFrame data is not copied — only the Index object holding the
    column labels is replaced.

    Args:
        df: DataFrame whose column headers may contain encoding artefacts.

    Returns:
        The same DataFrame with corrected column labels.
    """
    normalised = [_normalize_encoding(col) for col in df.columns]

    if normalised != list(df.columns):
        changed = [
            (raw, fixed)
            for raw, fixed in zip(df.columns, normalised)
            if raw != fixed
        ]
        logger.info(
            "Encoding normalisation fixed %d column header(s): %s",
            len(changed),
            changed,
        )

    return df.rename(columns=dict(zip(df.columns, normalised)))


# ---------------------------------------------------------------------------
# Canonical schema
# ---------------------------------------------------------------------------

# Maps raw OBD-II CSV headers  →  internal snake_case names.
# Defined at module level so other modules can import it when they need to
# reference the canonical column list (e.g. for validation in cleaner.py).
# All keys use the correct UTF-8 degree symbol; encoding normalisation runs
# before any lookup, so variants never need to appear here.
COLUMN_MAP: Final[dict[str, str]] = {
    "Time":                                          "timestamp",
    "Engine Coolant Temperature [°C]":               "coolant_temp",
    "Intake Manifold Absolute Pressure [kPa]":       "map",
    "Engine RPM [RPM]":                              "rpm",
    "Vehicle Speed Sensor [km/h]":                   "speed",
    "Intake Air Temperature [°C]":                   "iat",
    "Air Flow Rate from Mass Flow Sensor [g/s]":     "maf",
    "Absolute Throttle Position [%]":                "throttle_pos",
    "Ambient Air Temperature [°C]":                  "ambient_temp",
    "Accelerator Pedal Position D [%]":              "pedal_d",
    "Accelerator Pedal Position E [%]":              "pedal_e",
}

# Derived sets used by validation helpers and external callers.
REQUIRED_RAW_COLUMNS: Final[frozenset[str]] = frozenset(COLUMN_MAP.keys())
CANONICAL_COLUMNS: Final[frozenset[str]] = frozenset(COLUMN_MAP.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw OBD-II CSV headers to the canonical internal schema.

    Validates that every expected raw column is present before renaming.
    Extra columns that exist in the DataFrame but are not part of the known
    schema are preserved unchanged — they will be reviewed and either promoted
    to the schema or dropped in a later pipeline stage.

    Args:
        df: A DataFrame produced by :func:`loader.load_csv` or
            :func:`loader.load_csvs_from_directory`, still carrying the
            original OBD-II CSV headers.

    Returns:
        A new DataFrame with all required columns renamed to their canonical
        snake_case equivalents.  The original DataFrame is not mutated.

    Raises:
        TypeError:  If ``df`` is not a :class:`pandas.DataFrame`.
        ValueError: If one or more required raw columns are absent from ``df``.
                    The error message lists every missing column so the caller
                    can diagnose the issue in a single pass.

    Example::

        >>> raw_df = loader.load_csv("trip_001.csv")
        >>> std_df = standardize_columns(raw_df)
        >>> list(std_df.columns[:3])
        ['timestamp', 'coolant_temp', 'map']
    """
    _validate_input_type(df)
    df = _normalize_dataframe_columns(df)
    _validate_required_columns(df)

    standardized = df.rename(columns=COLUMN_MAP)

    extra_columns = [
        col for col in standardized.columns
        if col not in CANONICAL_COLUMNS
    ]
    if extra_columns:
        logger.warning(
            "Unrecognised column(s) kept as-is and will require review: %s",
            extra_columns,
        )

    logger.debug(
        "Standardised %d column(s). Extra column(s) preserved: %d",
        len(COLUMN_MAP),
        len(extra_columns),
    )

    return standardized


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _validate_input_type(df: pd.DataFrame) -> None:
    """Raise TypeError if *df* is not a pandas DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"Expected a pandas DataFrame, got {type(df).__name__!r}."
        )


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Raise ValueError listing every raw column absent from *df*.

    Reporting all missing columns at once (rather than stopping at the first)
    lets the caller correct the source data or column map in a single cycle
    instead of fixing one column and re-running repeatedly.
    """
    missing = sorted(REQUIRED_RAW_COLUMNS - set(df.columns))

    if missing:
        missing_display = "\n  ".join(f"• {col}" for col in missing)
        raise ValueError(
            f"{len(missing)} required column(s) missing from DataFrame:\n"
            f"  {missing_display}\n\n"
            f"Ensure the source CSV matches the expected OBD-II schema or "
            f"update COLUMN_MAP in standardizer.py."
        )