"""
ml/feature_engineering.py
==========================
Production feature engineering layer for the AutoAssist OBD-II anomaly
detection pipeline.

This module sits between state classification and Isolation Forest:

    Raw Telemetry → Preprocessing → State Classification
        → **Feature Engineering** → Isolation Forest → Health Score Engine

Responsibility
--------------
This module has exactly one responsibility: transform a preprocessed,
classified OBD-II DataFrame into a feature matrix ready for anomaly
detection.  It does not classify states, train models, or score health.

Feature set
-----------
Research established that *behavioural changes* are more diagnostic than
absolute sensor readings.  The final production feature set is therefore:

    Absolute values   : rpm, speed, maf, map, throttle_pos
    Delta features    : rpm_delta, speed_delta, maf_delta,
                        map_delta, throttle_delta

This set is frozen.  Do not add PCA, remove features, or introduce
additional engineered signals without a documented research decision.

Session isolation
-----------------
All delta features are computed **within each session** using
``groupby("session_id").diff()``.  Cross-session deltas would be
physically meaningless (two different trips) and are never calculated.

Usage
-----
    from ml.feature_engineering import FeatureEngineer

    engineer = FeatureEngineer()
    df_features = engineer.fit_transform(df_classified)

FastAPI integration
-------------------
``FeatureEngineer`` is a plain Python class with no global state.
Instantiate it once at application startup and share the instance across
requests, or instantiate per-request — both patterns are safe.

Real-time streaming
-------------------
For live OBD-II streams, call ``transform`` on each incoming window after
ensuring the window contains a sensible look-back buffer (at least one
prior row per session) so that the first-row NaN fill strategy produces
meaningful deltas.  See ``_compute_delta_features`` for details.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

import pandas as pd

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature set constants — single source of truth
# ---------------------------------------------------------------------------

# Absolute sensor columns that flow through unchanged.
_ABSOLUTE_FEATURES: Final[tuple[str, ...]] = (
    "rpm",
    "speed",
    "maf",
    "map",
    "throttle_pos",
)

# Columns for which session-scoped deltas are computed.
_DELTA_SOURCES: Final[tuple[str, ...]] = (
    "rpm",
    "speed",
    "maf",
    "map",
    "throttle_pos",
)

# Resulting delta column names (parallel to _DELTA_SOURCES).
_DELTA_FEATURES: Final[tuple[str, ...]] = (
    "rpm_delta",
    "speed_delta",
    "maf_delta",
    "map_delta",
    "throttle_delta",
)

# The complete production feature set presented to the anomaly detector.
PRODUCTION_FEATURES: Final[tuple[str, ...]] = _ABSOLUTE_FEATURES + _DELTA_FEATURES

# Columns that must be present in any input DataFrame.
_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {"session_id"} | set(_ABSOLUTE_FEATURES)
)


# ---------------------------------------------------------------------------
# Internal configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeatureEngineerConfig:
    """Immutable configuration for :class:`FeatureEngineer`.

    Keeping configuration in a dedicated dataclass makes it trivial to
    serialise, log, and pass through FastAPI request models without exposing
    constructor keyword arguments across the codebase.

    Attributes
    ----------
    fill_value:
        Scalar used to fill ``NaN`` values produced by ``.diff()`` on the
        first row of each session.

        Rationale for ``0.0``:
            The first sample of a session has no predecessor.  A delta of
            zero means "no change observed", which is the least biased
            assumption available without look-back data.  Alternatives such
            as forward-fill or dropping the row were rejected because:
            - Forward-fill leaks future information.
            - Dropping first rows silently shrinks the dataset and breaks
              index alignment with the classifier output.
            Zero-fill is transparent, deterministic, and safe for both
            batch and streaming workloads.

    preserve_non_feature_columns:
        When ``True``, all columns in the input that are not part of the
        production feature set are forwarded to the output DataFrame
        unchanged (e.g. ``session_id``, ``timestamp``, ``state``).
        Set to ``False`` to return only the production feature columns.
    """

    fill_value: float = 0.0
    preserve_non_feature_columns: bool = True


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_input(df: pd.DataFrame) -> None:
    """Validate the input DataFrame before feature engineering begins.

    Raises descriptive exceptions rather than allowing cryptic pandas errors
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
            f"FeatureEngineer.transform expects a pandas DataFrame, "
            f"got {type(df).__name__!r} instead."
        )

    if df.empty:
        raise ValueError(
            "FeatureEngineer.transform received an empty DataFrame. "
            "Ensure the preprocessing and classification pipeline completed "
            "successfully before calling feature engineering."
        )

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input DataFrame is missing required column(s): {sorted(missing)}. "
            f"Expected at minimum: {sorted(_REQUIRED_COLUMNS)}."
        )

    # Numeric dtype check — must follow the column-existence check above so
    # we never attempt to inspect a column that may not be present.
    # OBD-II sensor readings must be numeric; non-numeric values (e.g. a
    # string-typed column caused by a parsing error upstream) would silently
    # corrupt every delta calculation.
    for col in _ABSOLUTE_FEATURES:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(
                f"Column '{col}' must contain numeric values, "
                f"but dtype is '{df[col].dtype}'. "
                f"Check the preprocessing pipeline for type coercion errors."
            )

    logger.debug(
        "Input validation passed",
        extra={"rows": len(df), "columns": len(df.columns)},
    )


# ---------------------------------------------------------------------------
# Delta feature computation
# ---------------------------------------------------------------------------


def _compute_delta_features(
    df: pd.DataFrame,
    fill_value: float,
) -> pd.DataFrame:
    """Compute session-scoped delta features and append them to *df*.

    Each delta column is the row-to-row difference of its source column,
    calculated **independently within each session** via
    ``groupby("session_id").diff()``.  This prevents physically meaningless
    cross-session deltas (e.g. the RPM jump between the last sample of trip A
    and the first sample of trip B).

    First-row NaN handling
    ~~~~~~~~~~~~~~~~~~~~~~
    ``.diff()`` produces ``NaN`` for the first row of every session because
    there is no prior observation to subtract from.  These are filled with
    ``fill_value`` (default ``0.0``).  See :class:`FeatureEngineerConfig`
    for the rationale behind this choice.

    Parameters
    ----------
    df:
        DataFrame containing ``session_id`` and all ``_DELTA_SOURCES``
        columns.  Must already be validated.
    fill_value:
        Scalar used to replace first-row ``NaN`` values.

    Returns
    -------
    pandas.DataFrame
        *df* with all ``_DELTA_FEATURES`` columns appended in-place.
        The caller is responsible for ensuring *df* is already a copy.
    """
    session_groups = df.groupby("session_id", sort=False)

    for source, delta_col in zip(_DELTA_SOURCES, _DELTA_FEATURES):
        raw_delta: pd.Series = session_groups[source].diff()
        filled: pd.Series = raw_delta.fillna(fill_value)
        df[delta_col] = filled

        logger.info(
            "Generated feature",
            extra={
                "feature": delta_col,
                "null_count": int(raw_delta.isna().sum()),
                "fill_value": fill_value,
            },
        )

    return df


# ---------------------------------------------------------------------------
# FeatureEngineer class
# ---------------------------------------------------------------------------


class FeatureEngineer:
    """Deterministic feature engineering stage for the AutoAssist pipeline.

    Transforms a preprocessed OBD-II DataFrame into a feature matrix
    ready for Isolation Forest anomaly detection.

    The public API mirrors the scikit-learn transformer contract
    (``fit`` / ``transform`` / ``fit_transform``) so this class can be
    dropped into a scikit-learn ``Pipeline`` in the future if needed.

    Parameters
    ----------
    config:
        Optional :class:`FeatureEngineerConfig` instance.  If omitted,
        sensible production defaults are used.

    Examples
    --------
    >>> engineer = FeatureEngineer()
    >>> df_features = engineer.fit_transform(df_classified)
    >>> df_features[list(PRODUCTION_FEATURES)].describe()
    """

    def __init__(
        self,
        config: FeatureEngineerConfig | None = None,
    ) -> None:
        self._config: FeatureEngineerConfig = config or FeatureEngineerConfig()
        self._is_fitted: bool = False

        logger.debug(
            "FeatureEngineer initialised",
            extra={
                "fill_value": self._config.fill_value,
                "preserve_non_feature_columns": self._config.preserve_non_feature_columns,
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> "FeatureEngineer":
        """Fit the feature engineer to *df*.

        This method exists for future compatibility with stateful
        transformations (e.g. per-feature normalization statistics, rolling
        baseline calibration, or session-level z-score anchors).

        No statistical state is derived in the current implementation; the
        method simply validates the input and marks the instance as fitted.

        Parameters
        ----------
        df:
            Preprocessed OBD-II DataFrame.  Must contain all required
            columns defined in ``_REQUIRED_COLUMNS``.

        Returns
        -------
        FeatureEngineer
            The same instance, allowing ``engineer.fit(df).transform(df)``
            chaining.

        Raises
        ------
        TypeError
            If *df* is not a :class:`pandas.DataFrame`.
        ValueError
            If *df* is empty or is missing required columns.
        """
        _validate_input(df)
        self._is_fitted = True

        logger.info(
            "FeatureEngineer fitted",
            extra={"rows": len(df), "sessions": df["session_id"].nunique()},
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate the production feature matrix from *df*.

        Steps
        -----
        1. Validate input.
        2. Copy the DataFrame — the caller's object is never mutated.
        3. Compute session-scoped delta features.
        4. Return the enriched DataFrame (all columns or feature-only,
           depending on ``config.preserve_non_feature_columns``).

        Parameters
        ----------
        df:
            Preprocessed OBD-II DataFrame.  Must contain all required
            columns defined in ``_REQUIRED_COLUMNS``.

        Returns
        -------
        pandas.DataFrame
            Enriched DataFrame containing the full production feature set.
            If ``config.preserve_non_feature_columns`` is ``True``, all
            non-feature columns (``session_id``, ``timestamp``, ``state``,
            etc.) are preserved.  Otherwise only ``PRODUCTION_FEATURES``
            columns are returned.

        Raises
        ------
        TypeError
            If *df* is not a :class:`pandas.DataFrame`.
        ValueError
            If *df* is empty or is missing required columns.
        """
        _validate_input(df)

        logger.info(
            "Feature engineering started",
            extra={"rows": len(df), "sessions": df["session_id"].nunique()},
        )

        # Always work on a copy — never mutate the caller's DataFrame.
        result: pd.DataFrame = df.copy()

        # Sort by [session_id, timestamp] before computing deltas.
        # Correct delta values depend on rows being in chronological order
        # within each session.  Without sorting, an unsorted input would
        # produce deltas between non-consecutive observations, making the
        # engineered features physically meaningless.  We sort only when
        # timestamp is present; session_id is always included as the primary
        # key so that groupby() still produces session-scoped deltas.
        if "timestamp" in result.columns:
            result = result.sort_values(
                ["session_id", "timestamp"]
            ).reset_index(drop=True)

        # Compute all delta features in-place on the copy.
        result = _compute_delta_features(result, self._config.fill_value)

        # Optionally trim to production features only.
        if not self._config.preserve_non_feature_columns:
            available = [c for c in PRODUCTION_FEATURES if c in result.columns]
            result = result[available]
            logger.debug(
                "Non-feature columns dropped",
                extra={"retained_columns": available},
            )

        logger.info(
            "Feature engineering complete",
            extra={
                "output_rows": len(result),
                "output_columns": list(result.columns),
                "feature_columns": list(PRODUCTION_FEATURES),
            },
        )

        return result

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit to *df* and immediately return the transformed DataFrame.

        Convenience wrapper equivalent to::

            engineer.fit(df).transform(df)

        Parameters
        ----------
        df:
            Preprocessed OBD-II DataFrame.

        Returns
        -------
        pandas.DataFrame
            Enriched DataFrame containing the full production feature set.

        Raises
        ------
        TypeError
            If *df* is not a :class:`pandas.DataFrame`.
        ValueError
            If *df* is empty or is missing required columns.
        """
        return self.fit(df).transform(df)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def feature_names_out(self) -> tuple[str, ...]:
        """Return the ordered tuple of production feature column names.

        Mirrors the scikit-learn ``get_feature_names_out`` convention so
        this property can be consumed by downstream pipeline components
        without importing ``PRODUCTION_FEATURES`` directly.

        Returns
        -------
        tuple[str, ...]
            The frozen production feature set.
        """
        return PRODUCTION_FEATURES

    @property
    def is_fitted(self) -> bool:
        """``True`` if :meth:`fit` has been called at least once."""
        return self._is_fitted

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FeatureEngineer("
            f"fill_value={self._config.fill_value!r}, "
            f"preserve_non_feature_columns={self._config.preserve_non_feature_columns!r}, "
            f"is_fitted={self._is_fitted!r})"
        )