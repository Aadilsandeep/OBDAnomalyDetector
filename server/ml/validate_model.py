"""
ml/validate_model.py
====================
Behavioral validation script for the trained Isolation Forest model.

Pipeline position:

    Raw Telemetry → Preprocessing → State Classification
        → Feature Engineering → Anomaly Detection → Health Score Engine
                                        ↓
                              **Model Validation** (this module)

Responsibility
--------------
This module validates the *behavior* of the trained anomaly detection model
by running inference on the full training dataset and generating structured
analysis artifacts.  It does **not** perform supervised evaluation — there
are no anomaly labels in the dataset.

It does NOT:
- Retrain models
- Tune hyperparameters
- Modify health scoring
- Create API endpoints

Outputs
-------
    reports/
    ├── anomaly_summary.json              — overall anomaly statistics
    ├── state_anomaly_analysis.csv        — per-state anomaly breakdown
    ├── session_anomaly_analysis.csv      — per-session anomaly breakdown
    └── anomaly_score_distribution.csv    — score distribution statistics

Usage
-----
    python server/ml/validate_model.py

Design
------
All analysis functions are importable and callable independently for CI
pipelines, monitoring dashboards, and notebook-based exploration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd

from server.ml.anomaly_detector import (
    ANOMALY_FLAG_COLUMN,
    ANOMALY_SCORE_COLUMN,
    AnomalyDetector,
)
from server.analytics.state_classifier import classify_states

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants — resolved relative to project root
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DATA_PATH: Final[Path] = _PROJECT_ROOT / "data" / "processed" / "master_dataset.csv"
_REPORTS_DIR: Final[Path] = _PROJECT_ROOT / "reports"

# ---------------------------------------------------------------------------
# Required columns
# ---------------------------------------------------------------------------

_COL_STATE: Final[str] = "state"
_COL_SESSION_ID: Final[str] = "session_id"

# Analysis column names
_COL_ROW_COUNT: Final[str] = "row_count"
_COL_ANOMALY_COUNT: Final[str] = "anomaly_count"
_COL_ANOMALY_RATE: Final[str] = "anomaly_rate"


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationConfig:
    """Immutable configuration for the model validation pipeline.

    Attributes
    ----------
    data_path:
        Path to the master dataset CSV.
    reports_dir:
        Directory where validation artifacts are written.
    rate_precision:
        Number of decimal places for anomaly rate values.
    """

    data_path: Path = _DATA_PATH
    reports_dir: Path = _REPORTS_DIR
    rate_precision: int = 4


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_dataset(df: pd.DataFrame) -> None:
    """Validate the loaded dataset before running the pipeline.

    Parameters
    ----------
    df:
        Raw dataset loaded from disk.

    Raises
    ------
    ValueError
        If the DataFrame is empty.
    """
    if df.empty:
        raise ValueError(
            "Master dataset is empty. Verify that the preprocessing "
            "pipeline produced valid output before running validation."
        )

    logger.debug(
        "Dataset validation passed",
        extra={"rows": len(df), "columns": len(df.columns)},
    )


def _validate_anomaly_columns(df: pd.DataFrame) -> None:
    """Validate that anomaly detection output columns are present.

    Parameters
    ----------
    df:
        DataFrame after anomaly detection.

    Raises
    ------
    ValueError
        If required anomaly columns are missing.
    """
    required = {ANOMALY_SCORE_COLUMN, ANOMALY_FLAG_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame is missing anomaly column(s): {sorted(missing)}. "
            "Ensure AnomalyDetector.detect() ran successfully."
        )


def _validate_groupby_column(df: pd.DataFrame, column: str) -> None:
    """Validate that a grouping column exists in the DataFrame.

    Parameters
    ----------
    df:
        DataFrame to check.
    column:
        Column name required for grouping.

    Raises
    ------
    ValueError
        If the column is missing.
    """
    if column not in df.columns:
        raise ValueError(
            f"DataFrame is missing required column '{column}' for analysis."
        )


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------


def compute_anomaly_summary(
    df: pd.DataFrame,
    rate_precision: int = 4,
) -> dict[str, Any]:
    """Compute overall anomaly statistics from the detection output.

    Parameters
    ----------
    df:
        DataFrame containing ``anomaly_flag`` column.
    rate_precision:
        Decimal places for the anomaly rate.

    Returns
    -------
    dict[str, Any]
        Summary with ``total_records``, ``total_anomalies``, and
        ``anomaly_rate``.
    """
    _validate_anomaly_columns(df)

    total_records: int = len(df)
    total_anomalies: int = int(df[ANOMALY_FLAG_COLUMN].sum())
    anomaly_rate: float = round(
        total_anomalies / total_records if total_records else 0.0,
        rate_precision,
    )

    summary: dict[str, Any] = {
        "total_records": total_records,
        "total_anomalies": total_anomalies,
        "anomaly_rate": anomaly_rate,
    }

    logger.info(
        "Anomaly summary computed",
        extra=summary,
    )

    return summary


def compute_state_anomaly_analysis(
    df: pd.DataFrame,
    rate_precision: int = 4,
) -> pd.DataFrame:
    """Compute per-state anomaly breakdown.

    Parameters
    ----------
    df:
        DataFrame containing ``state`` and ``anomaly_flag`` columns.
    rate_precision:
        Decimal places for per-state anomaly rates.

    Returns
    -------
    pandas.DataFrame
        One row per driving state with ``row_count``, ``anomaly_count``,
        and ``anomaly_rate`` columns.
    """
    _validate_anomaly_columns(df)
    _validate_groupby_column(df, _COL_STATE)

    grouped: pd.DataFrame = (
        df.groupby(_COL_STATE, sort=True)
        .agg(
            row_count=(ANOMALY_FLAG_COLUMN, "count"),
            anomaly_count=(ANOMALY_FLAG_COLUMN, "sum"),
        )
        .reset_index()
    )

    grouped[_COL_ANOMALY_COUNT] = grouped[_COL_ANOMALY_COUNT].astype(int)
    grouped[_COL_ANOMALY_RATE] = (
        grouped[_COL_ANOMALY_COUNT] / grouped[_COL_ROW_COUNT]
    ).round(rate_precision)

    logger.info(
        "State anomaly analysis computed",
        extra={"states": len(grouped)},
    )

    return grouped


def compute_session_anomaly_analysis(
    df: pd.DataFrame,
    rate_precision: int = 4,
) -> pd.DataFrame:
    """Compute per-session anomaly breakdown, sorted by anomaly rate.

    Parameters
    ----------
    df:
        DataFrame containing ``session_id`` and ``anomaly_flag`` columns.
    rate_precision:
        Decimal places for per-session anomaly rates.

    Returns
    -------
    pandas.DataFrame
        One row per session with ``row_count``, ``anomaly_count``, and
        ``anomaly_rate`` columns, sorted descending by ``anomaly_rate``.
    """
    _validate_anomaly_columns(df)
    _validate_groupby_column(df, _COL_SESSION_ID)

    grouped: pd.DataFrame = (
        df.groupby(_COL_SESSION_ID, sort=False)
        .agg(
            row_count=(ANOMALY_FLAG_COLUMN, "count"),
            anomaly_count=(ANOMALY_FLAG_COLUMN, "sum"),
        )
        .reset_index()
    )

    grouped[_COL_ANOMALY_COUNT] = grouped[_COL_ANOMALY_COUNT].astype(int)
    grouped[_COL_ANOMALY_RATE] = (
        grouped[_COL_ANOMALY_COUNT] / grouped[_COL_ROW_COUNT]
    ).round(rate_precision)

    # Sort descending by anomaly rate — most anomalous sessions first.
    grouped = grouped.sort_values(
        _COL_ANOMALY_RATE, ascending=False
    ).reset_index(drop=True)

    logger.info(
        "Session anomaly analysis computed",
        extra={"sessions": len(grouped)},
    )

    return grouped


def compute_score_distribution(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute descriptive statistics for the anomaly score column.

    Parameters
    ----------
    df:
        DataFrame containing ``anomaly_score`` column.

    Returns
    -------
    pandas.DataFrame
        Single-row DataFrame with ``min``, ``max``, ``mean``, ``median``,
        and ``std`` columns.
    """
    _validate_anomaly_columns(df)

    scores: pd.Series = df[ANOMALY_SCORE_COLUMN]

    distribution: dict[str, float] = {
        "min": round(float(scores.min()), 4),
        "max": round(float(scores.max()), 4),
        "mean": round(float(scores.mean()), 4),
        "median": round(float(scores.median()), 4),
        "std": round(float(scores.std()), 4),
    }

    result: pd.DataFrame = pd.DataFrame([distribution])

    logger.info(
        "Anomaly score distribution computed",
        extra=distribution,
    )

    return result


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------


def _ensure_reports_dir(reports_dir: Path) -> None:
    """Create the reports directory if it does not exist.

    Parameters
    ----------
    reports_dir:
        Target directory path.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Reports directory ready", extra={"path": str(reports_dir)})


def _save_json(data: dict[str, Any], path: Path) -> None:
    """Write a dict to disk as formatted JSON.

    Parameters
    ----------
    data:
        JSON-serialisable dict.
    path:
        Destination file path.
    """
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Artifact saved", extra={"path": str(path), "type": "json"})


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to disk as CSV.

    Parameters
    ----------
    df:
        DataFrame to persist.
    path:
        Destination file path.
    """
    df.to_csv(path, index=False)
    logger.info(
        "Artifact saved",
        extra={"path": str(path), "type": "csv", "rows": len(df)},
    )


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


def run_validation(config: ValidationConfig | None = None) -> dict[str, Any]:
    """Execute the full model validation pipeline.

    Steps
    -----
    1. Load the master dataset.
    2. Run state classification (adds ``state`` column).
    3. Run anomaly detection via ``AnomalyDetector.detect()``.
    4. Compute all analyses.
    5. Persist validation artifacts to ``reports/``.

    Parameters
    ----------
    config:
        Optional :class:`ValidationConfig`.  If omitted, production
        defaults are used.

    Returns
    -------
    dict[str, Any]
        The overall anomaly summary dict.

    Raises
    ------
    FileNotFoundError
        If the master dataset does not exist.
    ValueError
        If the dataset is empty or missing required columns.
    """
    cfg: ValidationConfig = config or ValidationConfig()

    logger.info(
        "Model validation started",
        extra={"data_path": str(cfg.data_path), "reports_dir": str(cfg.reports_dir)},
    )

    # ------------------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------------------
    if not cfg.data_path.exists():
        raise FileNotFoundError(
            f"Master dataset not found at '{cfg.data_path}'. "
            "Run the preprocessing pipeline before validation."
        )

    logger.info("Loading dataset", extra={"path": str(cfg.data_path)})
    df_raw: pd.DataFrame = pd.read_csv(cfg.data_path)
    _validate_dataset(df_raw)

    logger.info(
        "Dataset loaded",
        extra={"rows": len(df_raw), "columns": list(df_raw.columns)},
    )

    # ------------------------------------------------------------------
    # 2. State classification
    # ------------------------------------------------------------------
    logger.info("Running state classification")
    df_classified, classification_report = classify_states(df_raw)
    classification_report.log()

    logger.info(
        "State classification complete",
        extra={"output_columns": list(df_classified.columns)},
    )

    # ------------------------------------------------------------------
    # 3. Anomaly detection
    # ------------------------------------------------------------------
    logger.info("Running anomaly detection")
    detector = AnomalyDetector()
    df_detected: pd.DataFrame = detector.detect(df_classified)

    logger.info(
        "Anomaly detection complete",
        extra={
            "output_rows": len(df_detected),
            "output_columns": list(df_detected.columns),
        },
    )

    # ------------------------------------------------------------------
    # 4. Analyses
    # ------------------------------------------------------------------
    logger.info("Computing validation analyses")

    summary: dict[str, Any] = compute_anomaly_summary(
        df_detected, rate_precision=cfg.rate_precision
    )

    state_analysis: pd.DataFrame = compute_state_anomaly_analysis(
        df_detected, rate_precision=cfg.rate_precision
    )

    session_analysis: pd.DataFrame = compute_session_anomaly_analysis(
        df_detected, rate_precision=cfg.rate_precision
    )

    score_distribution: pd.DataFrame = compute_score_distribution(df_detected)

    # ------------------------------------------------------------------
    # 5. Persist artifacts
    # ------------------------------------------------------------------
    _ensure_reports_dir(cfg.reports_dir)

    _save_json(summary, cfg.reports_dir / "anomaly_summary.json")
    _save_csv(state_analysis, cfg.reports_dir / "state_anomaly_analysis.csv")
    _save_csv(session_analysis, cfg.reports_dir / "session_anomaly_analysis.csv")
    _save_csv(score_distribution, cfg.reports_dir / "anomaly_score_distribution.csv")

    logger.info(
        "Model validation complete",
        extra={
            "summary": summary,
            "reports_dir": str(cfg.reports_dir),
            "artifacts_generated": 4,
        },
    )

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    run_validation()
