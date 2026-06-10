"""
ml/anomaly_detector.py
======================
Inference-only anomaly detection module for the AutoAssist OBD-II pipeline.

Pipeline position:

    Raw Telemetry → Preprocessing → State Classification
        → Feature Engineering → **Anomaly Detection** → (future) Health Score Engine

Responsibility
--------------
This module has exactly **one** responsibility: load pre-trained artifacts and
run inference on new OBD-II data to produce anomaly scores and binary flags.

It does NOT:
- Train models
- Fit scalers
- Tune hyperparameters
- Compute health scores
- Expose API endpoints

Trained artifacts consumed
--------------------------
    models/
    ├── isolation_forest.pkl   — trained IsolationForest
    ├── scaler.pkl             — fitted StandardScaler
    └── feature_config.json    — ordered feature column list

Usage
-----
    from server.ml.anomaly_detector import AnomalyDetector

    detector = AnomalyDetector()
    df_result = detector.detect(df_preprocessed)

FastAPI integration
-------------------
``AnomalyDetector`` is a plain Python class with no global mutable state.
Instantiate it once at application startup (e.g. in a ``lifespan`` handler)
and inject it into route handlers via ``Depends()``.  The ``detect`` method
is stateless and thread-safe for concurrent request serving.

Real-time streaming
-------------------
For live OBD-II streams, call ``detect`` on each incoming window.  Ensure the
window contains a sensible look-back buffer (≥ 1 prior row per session) so
that the ``FeatureEngineer`` delta computation produces meaningful values.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from server.ml.feature_engineering import FeatureEngineer

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default artifact paths — resolved relative to project root
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DEFAULT_MODELS_DIR: Final[Path] = _PROJECT_ROOT / "models"

# ---------------------------------------------------------------------------
# Output column names — single source of truth for downstream consumers
# ---------------------------------------------------------------------------

ANOMALY_SCORE_COLUMN: Final[str] = "anomaly_score"
ANOMALY_FLAG_COLUMN: Final[str] = "anomaly_flag"


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnomalyDetectorConfig:
    """Immutable configuration for :class:`AnomalyDetector`.

    Keeping configuration in a dedicated dataclass makes it trivial to
    serialise, log, and pass through FastAPI dependency injection without
    exposing constructor keyword arguments across the codebase.

    Attributes
    ----------
    models_dir:
        Directory containing the trained artifacts.  Defaults to
        ``<project_root>/models/``.
    model_filename:
        Filename of the serialised ``IsolationForest`` inside *models_dir*.
    scaler_filename:
        Filename of the serialised ``StandardScaler`` inside *models_dir*.
    feature_config_filename:
        Filename of the JSON feature configuration inside *models_dir*.
    """

    models_dir: Path = field(default_factory=lambda: _DEFAULT_MODELS_DIR)
    model_filename: str = "isolation_forest.pkl"
    scaler_filename: str = "scaler.pkl"
    feature_config_filename: str = "feature_config.json"

    # -- Derived paths (not set by caller) ----------------------------------

    @property
    def model_path(self) -> Path:
        """Absolute path to the serialised IsolationForest."""
        return self.models_dir / self.model_filename

    @property
    def scaler_path(self) -> Path:
        """Absolute path to the serialised StandardScaler."""
        return self.models_dir / self.scaler_filename

    @property
    def feature_config_path(self) -> Path:
        """Absolute path to the feature configuration JSON."""
        return self.models_dir / self.feature_config_filename


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_inference_input(
    df: pd.DataFrame,
    feature_columns: list[str],
) -> None:
    """Validate the input DataFrame before inference begins.

    Raises descriptive exceptions rather than allowing cryptic downstream
    errors to propagate.

    Parameters
    ----------
    df:
        DataFrame to validate.
    feature_columns:
        Ordered list of feature column names expected after feature
        engineering.

    Raises
    ------
    TypeError
        If *df* is not a :class:`pandas.DataFrame`.
    ValueError
        If *df* is empty, is missing required features, or contains
        NaN / infinite values in the feature columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"AnomalyDetector.detect expects a pandas DataFrame, "
            f"got {type(df).__name__!r} instead."
        )

    if df.empty:
        raise ValueError(
            "AnomalyDetector.detect received an empty DataFrame. "
            "Ensure the preprocessing pipeline completed successfully "
            "before calling anomaly detection."
        )

    # --- Required feature columns -----------------------------------------

    missing = set(feature_columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame is missing required feature column(s) after "
            f"feature engineering: {sorted(missing)}. "
            f"Expected columns: {feature_columns}."
        )

    # --- NaN check --------------------------------------------------------

    feature_df: pd.DataFrame = df[feature_columns]
    nan_counts: pd.Series = feature_df.isna().sum()
    columns_with_nan = nan_counts[nan_counts > 0]
    if not columns_with_nan.empty:
        raise ValueError(
            f"Feature columns contain NaN values: "
            f"{columns_with_nan.to_dict()}. "
            "Resolve upstream in the preprocessing or feature engineering "
            "stage before running inference."
        )

    # --- Infinite value check ---------------------------------------------

    if not np.isfinite(feature_df.to_numpy()).all():
        non_finite_cols = [
            col
            for col in feature_columns
            if not np.isfinite(feature_df[col].to_numpy()).all()
        ]
        raise ValueError(
            f"Feature columns contain infinite values: {non_finite_cols}. "
            "Resolve upstream in the preprocessing or feature engineering "
            "stage before running inference."
        )

    logger.debug(
        "Inference input validation passed",
        extra={"rows": len(df), "feature_count": len(feature_columns)},
    )


# ---------------------------------------------------------------------------
# AnomalyDetector class
# ---------------------------------------------------------------------------


class AnomalyDetector:
    """Inference-only anomaly detector for the AutoAssist OBD-II pipeline.

    Loads pre-trained artifacts at construction time and exposes a single
    public method :meth:`detect` that accepts a preprocessed DataFrame and
    returns it enriched with anomaly scores and binary flags.

    Parameters
    ----------
    config:
        Optional :class:`AnomalyDetectorConfig` instance.  If omitted,
        default production paths are used.

    Raises
    ------
    FileNotFoundError
        If any required artifact file does not exist on disk.

    Examples
    --------
    >>> detector = AnomalyDetector()
    >>> df_result = detector.detect(df_preprocessed)
    >>> df_result[["anomaly_score", "anomaly_flag"]].describe()
    """

    def __init__(
        self,
        config: AnomalyDetectorConfig | None = None,
    ) -> None:
        self._config: AnomalyDetectorConfig = config or AnomalyDetectorConfig()

        logger.info(
            "AnomalyDetector initialising",
            extra={"models_dir": str(self._config.models_dir)},
        )

        # Load all artifacts — fail fast if anything is missing.
        self._model: IsolationForest = self._load_model()
        self._scaler: StandardScaler = self._load_scaler()
        self._feature_columns: list[str] = self._load_feature_config()
        self._feature_engineer: FeatureEngineer = FeatureEngineer()

        logger.info(
            "AnomalyDetector ready",
            extra={
                "model_path": str(self._config.model_path),
                "scaler_path": str(self._config.scaler_path),
                "feature_config_path": str(self._config.feature_config_path),
                "feature_count": len(self._feature_columns),
            },
        )

    # ------------------------------------------------------------------
    # Artifact loaders
    # ------------------------------------------------------------------

    def _load_model(self) -> IsolationForest:
        """Deserialise the trained IsolationForest from disk.

        Returns
        -------
        IsolationForest
            Pre-trained model instance.

        Raises
        ------
        FileNotFoundError
            If the model file does not exist.
        """
        path = self._config.model_path
        if not path.exists():
            raise FileNotFoundError(
                f"Trained IsolationForest not found at '{path}'. "
                "Run the training pipeline before starting inference."
            )
        model: IsolationForest = joblib.load(path)
        logger.info("IsolationForest loaded", extra={"path": str(path)})
        return model

    def _load_scaler(self) -> StandardScaler:
        """Deserialise the fitted StandardScaler from disk.

        Returns
        -------
        StandardScaler
            Pre-fitted scaler instance.

        Raises
        ------
        FileNotFoundError
            If the scaler file does not exist.
        """
        path = self._config.scaler_path
        if not path.exists():
            raise FileNotFoundError(
                f"Fitted StandardScaler not found at '{path}'. "
                "Run the training pipeline before starting inference."
            )
        scaler: StandardScaler = joblib.load(path)
        logger.info("StandardScaler loaded", extra={"path": str(path)})
        return scaler

    def _load_feature_config(self) -> list[str]:
        """Load the ordered feature column list from the JSON config.

        The feature config preserves the exact column order used during
        training.  Loading without this file risks silent column-order
        mismatches between the scaler / model and the inference matrix.

        Returns
        -------
        list[str]
            Ordered feature column names.

        Raises
        ------
        FileNotFoundError
            If the feature config file does not exist.
        ValueError
            If the JSON is malformed or missing the ``feature_columns`` key.
        """
        path = self._config.feature_config_path
        if not path.exists():
            raise FileNotFoundError(
                f"Feature config not found at '{path}'. "
                "Run the training pipeline before starting inference."
            )

        raw: dict = json.loads(path.read_text(encoding="utf-8"))

        if "feature_columns" not in raw:
            raise ValueError(
                f"Feature config at '{path}' is missing the "
                "'feature_columns' key. Expected format: "
                '{"feature_columns": ["col1", "col2", ...]}.'
            )

        columns: list[str] = raw["feature_columns"]

        if not columns:
            raise ValueError(
                f"Feature config at '{path}' contains an empty "
                "'feature_columns' list. At least one feature is required."
            )

        logger.info(
            "Feature config loaded",
            extra={"path": str(path), "features": columns},
        )
        return columns

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run anomaly detection on a preprocessed OBD-II DataFrame.

        Processing pipeline::

            DataFrame
                ↓
            FeatureEngineer.transform()
                ↓
            Feature Selection (ordered columns from feature_config.json)
                ↓
            StandardScaler.transform()
                ↓
            IsolationForest.decision_function()  →  anomaly_score
                ↓
            IsolationForest.predict()            →  anomaly_flag

        Anomaly flag convention::

            sklearn output      AutoAssist convention
            ──────────────      ─────────────────────
             1  (inlier)   →   0  (normal)
            -1  (outlier)  →   1  (anomaly)

        Parameters
        ----------
        df:
            Preprocessed OBD-II DataFrame.  Must contain all columns
            required by :class:`FeatureEngineer` (``session_id`` and the
            five absolute sensor columns).

        Returns
        -------
        pandas.DataFrame
            A copy of the input enriched with two additional columns:

            - ``anomaly_score`` : float — raw decision function output
              from the Isolation Forest (lower = more anomalous).
            - ``anomaly_flag`` : int — binary label where ``0`` = normal
              and ``1`` = anomaly.

        Raises
        ------
        TypeError
            If *df* is not a :class:`pandas.DataFrame`.
        ValueError
            If *df* is empty, missing required columns, or contains
            NaN / infinite values in feature columns.
        """
        logger.info(
            "Anomaly detection started",
            extra={"input_rows": len(df), "input_columns": len(df.columns)},
        )

        # 1. Feature engineering -------------------------------------------
        df_engineered: pd.DataFrame = self._feature_engineer.transform(df)

        logger.debug(
            "Feature engineering complete",
            extra={
                "engineered_rows": len(df_engineered),
                "engineered_columns": list(df_engineered.columns),
            },
        )

        # 2. Validate engineered output ------------------------------------
        _validate_inference_input(df_engineered, self._feature_columns)

        # 3. Feature selection (exact column order from training) ----------
        feature_matrix: pd.DataFrame = df_engineered[self._feature_columns].copy()

        logger.debug(
            "Feature matrix extracted",
            extra={
                "shape": str(feature_matrix.shape),
                "columns": list(feature_matrix.columns),
            },
        )

        # 4. Scale features ------------------------------------------------
        scaled: np.ndarray = self._scaler.transform(feature_matrix)

        logger.debug("Features scaled", extra={"shape": str(scaled.shape)})

        # 5. Inference -----------------------------------------------------
        scores: np.ndarray = self._model.decision_function(scaled)
        predictions: np.ndarray = self._model.predict(scaled)

        # 6. Convert sklearn convention → AutoAssist convention ------------
        #    sklearn:     1 = inlier,  -1 = outlier
        #    AutoAssist:  0 = normal,   1 = anomaly
        anomaly_flags: np.ndarray = np.where(predictions == 1, 0, 1)

        # 7. Build result DataFrame ----------------------------------------
        result: pd.DataFrame = df_engineered.copy()
        result[ANOMALY_SCORE_COLUMN] = scores
        result[ANOMALY_FLAG_COLUMN] = anomaly_flags

        # Summary statistics for observability
        n_anomalies: int = int(anomaly_flags.sum())
        n_total: int = len(anomaly_flags)

        logger.info(
            "Anomaly detection complete",
            extra={
                "total_samples": n_total,
                "anomalies_detected": n_anomalies,
                "anomaly_rate": round(n_anomalies / n_total, 4) if n_total else 0.0,
                "score_min": round(float(scores.min()), 4) if n_total else None,
                "score_max": round(float(scores.max()), 4) if n_total else None,
                "score_mean": round(float(scores.mean()), 4) if n_total else None,
            },
        )

        return result

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def feature_columns(self) -> list[str]:
        """Return the ordered list of feature column names used for inference.

        This matches the column order persisted in ``feature_config.json``
        during training.
        """
        return list(self._feature_columns)

    @property
    def config(self) -> AnomalyDetectorConfig:
        """Return the active configuration (read-only — dataclass is frozen)."""
        return self._config

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AnomalyDetector("
            f"models_dir={str(self._config.models_dir)!r}, "
            f"features={len(self._feature_columns)})"
        )
