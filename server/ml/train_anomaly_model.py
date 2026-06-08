"""
ml/train_anomaly_model.py
=========================
Baseline training script for the AutoAssist OBD-II anomaly detection pipeline.

Pipeline position:

    Raw Telemetry → Preprocessing → State Classification
        → Feature Engineering → **Isolation Forest** → Health Score Engine

Responsibilities
----------------
1. Load the preprocessed master dataset from ``data/processed/master_dataset.csv``.
2. Apply ``FeatureEngineer`` to produce the production feature matrix.
3. Validate the training matrix (shape, missing columns, NaN, Inf).
4. Fit a ``StandardScaler`` on the feature matrix.
5. Train an ``IsolationForest`` on the scaled features.
6. Persist the scaler, model, and feature configuration to ``models/``.

Outputs
-------
    models/
    ├── isolation_forest.pkl   — trained IsolationForest
    ├── scaler.pkl             — fitted StandardScaler
    └── feature_config.json   — ordered feature column list for inference

Usage
-----
    python server/ml/train_anomaly_model.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from server.ml.feature_engineering import FeatureEngineer, PRODUCTION_FEATURES

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants — script must be run from the project root
# ---------------------------------------------------------------------------

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

_DATA_PATH: Final[Path] = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "master_dataset.csv"
)

_MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"
_MODEL_PATH: Final[Path] = _MODELS_DIR / "isolation_forest.pkl"
_SCALER_PATH: Final[Path] = _MODELS_DIR / "scaler.pkl"
_FEATURE_CONFIG_PATH: Final[Path] = _MODELS_DIR / "feature_config.json"

# ---------------------------------------------------------------------------
# Production feature set — imported directly from feature_engineering so that
# training and inference can never drift out of sync.  The tuple is immutable;
# the feature set is frozen and must not be modified here.
# ---------------------------------------------------------------------------

FEATURE_COLUMNS: Final[tuple[str, ...]] = PRODUCTION_FEATURES

# ---------------------------------------------------------------------------
# Model configuration — baseline production settings; do not tune here
# ---------------------------------------------------------------------------

_MODEL_CONFIG: Final[dict[str, object]] = {
    "n_estimators": 200,
    "contamination": "auto",
    "random_state": 42,
    "n_jobs": -1,
}


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------


def load_dataset(path: Path) -> pd.DataFrame:
    """Load the master dataset from *path*.

    Parameters
    ----------
    path:
        Absolute path to the CSV file produced by the preprocessing pipeline.

    Returns
    -------
    pandas.DataFrame
        Raw dataset exactly as stored on disk.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the loaded DataFrame is empty.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Master dataset not found at '{path}'. "
            "Ensure the preprocessing pipeline has been run before training."
        )

    logger.info("Loading dataset", extra={"path": str(path)})
    df: pd.DataFrame = pd.read_csv(path)

    if df.empty:
        raise ValueError(
            f"Dataset at '{path}' is empty. "
            "Verify that the preprocessing pipeline produced valid output."
        )

    logger.info(
        "Dataset loaded",
        extra={"rows": len(df), "columns": len(df.columns), "shape": str(df.shape)},
    )
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the production ``FeatureEngineer`` to *df*.

    Parameters
    ----------
    df:
        Raw or preprocessed OBD-II DataFrame.

    Returns
    -------
    pandas.DataFrame
        DataFrame enriched with all production feature columns.
    """
    logger.info("Running feature engineering", extra={"input_rows": len(df)})

    engineer = FeatureEngineer()
    df_features: pd.DataFrame = engineer.fit_transform(df)

    logger.info(
        "Feature engineering complete",
        extra={"output_rows": len(df_features), "output_columns": list(df_features.columns)},
    )
    return df_features


def build_training_matrix(df: pd.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    """Extract and validate the feature matrix used for model training.

    Validation checks (in order):
    1. All required feature columns are present.
    2. The resulting matrix is not empty.
    3. No NaN values exist in any feature column.
    4. No infinite values exist in any feature column.

    Parameters
    ----------
    df:
        Feature-engineered DataFrame produced by :func:`engineer_features`.
    feature_columns:
        Ordered tuple of column names that form the training matrix.

    Returns
    -------
    pandas.DataFrame
        Validated feature matrix with columns in the order defined by
        *feature_columns*.

    Raises
    ------
    ValueError
        If any validation check fails.
    """
    # 1. Missing columns
    missing = set(feature_columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"Feature matrix is missing column(s): {sorted(missing)}. "
            "Verify that FeatureEngineer produced the expected output."
        )

    print(df.columns.tolist())
    matrix: pd.DataFrame = df.loc[:, list(feature_columns)].copy()
    logger.info(
    f"Training matrix shape: {matrix.shape}"
    )

    # 2. Empty matrix
    if matrix.empty:
        raise ValueError(
            "Training matrix is empty after column selection. "
            "Check the dataset and feature engineering pipeline."
        )

    # 3. NaN values
    nan_counts: pd.Series = matrix.isna().sum()
    columns_with_nan = nan_counts[nan_counts > 0]
    if not columns_with_nan.empty:
        raise ValueError(
            f"Training matrix contains NaN values in column(s): "
            f"{columns_with_nan.to_dict()}. "
            "Resolve upstream in the preprocessing or feature engineering stage."
        )

    # 4. Infinite values — np.isfinite on the raw numpy array is significantly
    #    faster than DataFrame.isin() on multi-million-row datasets because it
    #    avoids Python-level iteration and operates on a contiguous C array.
    if not np.isfinite(matrix.to_numpy()).all():
        # Identify which columns contain non-finite values for the error message.
        non_finite_cols = [
            col for col in matrix.columns
            if not np.isfinite(matrix[col].to_numpy()).all()
        ]
        raise ValueError(
            f"Training matrix contains infinite values in column(s): "
            f"{non_finite_cols}. "
            "Resolve upstream in the preprocessing or feature engineering stage."
        )

    logger.info(
        "Training matrix validated",
        extra={"rows": len(matrix), "features": feature_columns},
    )
    return matrix


def fit_scaler(matrix: pd.DataFrame) -> tuple[StandardScaler, np.ndarray]:
    """Fit a ``StandardScaler`` on *matrix* and return the scaler and scaled array.

    Parameters
    ----------
    matrix:
        Validated training feature matrix.

    Returns
    -------
    scaler : StandardScaler
        Fitted scaler instance.
    scaled : numpy.ndarray
        Scaled feature array ready for model training.
    """
    logger.info("Fitting StandardScaler", extra={"features": list(matrix.columns)})

    scaler = StandardScaler()
    scaled: np.ndarray = scaler.fit_transform(matrix)

    logger.info(
        "StandardScaler fitted",
        extra={"n_features": scaler.n_features_in_},
    )
    return scaler, scaled


def train_model(scaled: np.ndarray) -> IsolationForest:
    """Train an ``IsolationForest`` on the scaled feature array.

    Model configuration is fixed at baseline production settings.
    Do not add cross-validation or hyperparameter search here.

    Parameters
    ----------
    scaled:
        Scaled training matrix produced by :func:`fit_scaler`.

    Returns
    -------
    IsolationForest
        Trained model instance.
    """
    logger.info("Training IsolationForest", extra={"config": _MODEL_CONFIG, "samples": len(scaled)})

    model = IsolationForest(**_MODEL_CONFIG)
    model.fit(scaled)

    logger.info(
        "IsolationForest training complete",
        extra={
            "n_estimators": model.n_estimators,
            "contamination": str(model.contamination),
            "training_samples": len(scaled),
        },
    )
    return model


def ensure_models_dir(models_dir: Path) -> None:
    """Create *models_dir* and any missing parents if they do not exist.

    Parameters
    ----------
    models_dir:
        Target directory path.
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Models directory ready", extra={"path": str(models_dir)})


def save_model(model: IsolationForest, path: Path) -> None:
    """Persist *model* to *path* using joblib.

    Parameters
    ----------
    model:
        Trained ``IsolationForest`` instance.
    path:
        Destination file path (e.g. ``models/isolation_forest.pkl``).
    """
    joblib.dump(model, path)
    logger.info("Model saved", extra={"path": str(path)})


def save_scaler(scaler: StandardScaler, path: Path) -> None:
    """Persist *scaler* to *path* using joblib.

    Parameters
    ----------
    scaler:
        Fitted ``StandardScaler`` instance.
    path:
        Destination file path (e.g. ``models/scaler.pkl``).
    """
    joblib.dump(scaler, path)
    logger.info("Scaler saved", extra={"path": str(path)})


def save_feature_config(feature_columns: tuple[str, ...], path: Path) -> None:
    """Write the ordered feature column list to *path* as JSON.

    The feature config preserves the exact column order expected by the
    inference pipeline (``anomaly_detector.py``).  Loading the model
    without this file risks silent column-order mismatches.

    Parameters
    ----------
    feature_columns:
        Ordered production feature list.
    path:
        Destination file path (e.g. ``models/feature_config.json``).
    """
    config: dict[str, list[str]] = {"feature_columns": list(feature_columns)}
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    logger.info("Feature config saved", extra={"path": str(path), "features": feature_columns})


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_training() -> None:
    """Execute the full training pipeline end-to-end.

    Steps
    -----
    1. Load dataset.
    2. Engineer features.
    3. Build and validate training matrix.
    4. Fit scaler.
    5. Train model.
    6. Persist artefacts.
    """
    logger.info("AutoAssist anomaly model training started")

    # 1. Load
    df_raw = load_dataset(_DATA_PATH)

    # 2. Feature engineering
    df_features = engineer_features(df_raw)

    # 3. Training matrix
    matrix = build_training_matrix(df_features, FEATURE_COLUMNS)

    # Guard against accidentally training on a corrupted or truncated dataset.
    # A matrix with fewer than 100 rows almost certainly indicates a pipeline
    # failure upstream rather than a legitimate training run.
    if len(matrix) < 100:
        raise ValueError(
            f"Training dataset is unexpectedly small ({len(matrix)} rows). "
            "Verify that the preprocessing pipeline produced valid output "
            "before attempting to train."
        )

    # 4. Scaler
    scaler, scaled = fit_scaler(matrix)

    # 5. Model
    model = train_model(scaled)

    # 6. Persist
    ensure_models_dir(_MODELS_DIR)
    save_model(model, _MODEL_PATH)
    save_scaler(scaler, _SCALER_PATH)
    save_feature_config(FEATURE_COLUMNS, _FEATURE_CONFIG_PATH)

    logger.info(
        "Training pipeline complete",
        extra={
            "model": str(_MODEL_PATH),
            "scaler": str(_SCALER_PATH),
            "feature_config": str(_FEATURE_CONFIG_PATH),
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_training()