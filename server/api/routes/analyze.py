"""
api/routes/analyze.py
=====================
CSV upload and full analysis pipeline endpoint.

``POST /api/analyze``

Accepts a multipart CSV file upload, runs the complete pipeline::

    CSV → read_csv → standardize → clean → classify_states
        → AnomalyDetector.detect → HealthScoreEngine.calculate
        → enrich (severity) → create session → return session_id

This endpoint is the only write operation in the API.  All other
endpoints are read-only lookups against the session store.
"""

from __future__ import annotations

import io
import logging
from typing import Final

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from server.analytics.state_classifier import classify_states
from server.analytics.state_analyzer import analyze_states
from server.api.dependencies import (
    get_detector,
    get_health_engine,
    get_session_service,
)
from server.api.schemas.analyze import AnalyzeResponse
from server.api.services.enrichment import enrich_anomalies
from server.api.services.session_service import SessionService
from server.ml.anomaly_detector import AnomalyDetector
from server.ml.health_score import HealthScoreEngine
from server.preprocessing.standardizer import standardize_columns
from server.preprocessing.cleaner import clean_dataframe

# ---------------------------------------------------------------------------
# Module-level logger & router
# ---------------------------------------------------------------------------

logger: Final[logging.Logger] = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    summary="Analyse an OBD-II CSV file",
    description="Upload a CSV file to run the full ML pipeline and create an analysis session.",
)
async def analyze_csv(
    file: UploadFile,
    detector: AnomalyDetector = Depends(get_detector),
    health_engine: HealthScoreEngine = Depends(get_health_engine),
    session_service: SessionService = Depends(get_session_service),
) -> AnalyzeResponse:
    """Execute the full analysis pipeline on an uploaded CSV.

    Parameters
    ----------
    file:
        Multipart file upload containing OBD-II telemetry data in CSV format.
    detector:
        Injected ``AnomalyDetector`` singleton.
    health_engine:
        Injected ``HealthScoreEngine`` singleton.
    session_service:
        Injected ``SessionService`` singleton.

    Returns
    -------
    AnalyzeResponse
        Session ID and summary statistics.

    Raises
    ------
    HTTPException 400
        If the file is not a CSV, is empty, or cannot be parsed.
    HTTPException 422
        If the CSV is missing required OBD-II columns.
    HTTPException 500
        If an unexpected error occurs during inference.
    """
    filename = file.filename or "upload.csv"

    logger.info("CSV upload received", extra={"upload_filename": filename})

    # ------------------------------------------------------------------
    # 1. Validate file type
    # ------------------------------------------------------------------
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Expected a .csv file, received '{filename}'.",
        )

    # ------------------------------------------------------------------
    # 2. Read file contents
    # ------------------------------------------------------------------
    try:
        contents = await file.read()
        if not contents or len(contents.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV file is empty.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read uploaded file: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 3. Parse CSV into DataFrame
    # ------------------------------------------------------------------
    try:
        df_raw = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV file has no parseable content.",
        )
    except pd.errors.ParserError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"CSV parsing failed: {exc}",
        )

    if df_raw.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV parsed successfully but contains no data rows.",
        )

    logger.info(
        "CSV parsed",
        extra={"rows": len(df_raw), "columns": len(df_raw.columns)},
    )

    # ------------------------------------------------------------------
    # 4. Preprocessing: standardize + clean
    # ------------------------------------------------------------------
    try:
        df_standardized = standardize_columns(df_raw)
        df_cleaned, _cleaning_report = clean_dataframe(df_standardized)
    except (TypeError, ValueError) as exc:
        logger.warning("Preprocessing failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=422,
            detail=f"CSV preprocessing failed: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 5. State classification
    # ------------------------------------------------------------------
    try:
        # Inject a session_id column for the single-file upload
        df_cleaned["session_id"] = filename.rsplit(".", 1)[0]
        df_classified, _classification_report = classify_states(df_cleaned)
    except (TypeError, ValueError) as exc:
        logger.warning("State classification failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=422,
            detail=f"State classification failed: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 6. Anomaly detection
    # ------------------------------------------------------------------
    try:
        df_anomalies = detector.detect(df_classified)
    except (TypeError, ValueError) as exc:
        logger.warning("Anomaly detection failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=422,
            detail=f"Anomaly detection failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected inference error")
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 7. Health score calculation
    # ------------------------------------------------------------------
    try:
        health_result = health_engine.calculate(df_anomalies)
    except (TypeError, ValueError) as exc:
        logger.warning("Health scoring failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=422,
            detail=f"Health scoring failed: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 8. Severity enrichment
    # ------------------------------------------------------------------
    df_enriched = enrich_anomalies(df_anomalies)

    # ------------------------------------------------------------------
    # 9. State analysis (dashboard metrics)
    # ------------------------------------------------------------------
    try:
        state_analysis, _analysis_report = analyze_states(df_enriched)
    except (TypeError, ValueError) as exc:
        logger.warning("State analysis failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=422,
            detail=f"State analysis failed: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # 10. Create session
    # ------------------------------------------------------------------
    session = session_service.create_session(
        filename=filename,
        df_enriched=df_enriched,
        health_result=health_result,
        state_analysis=state_analysis,
    )

    logger.info(
        "Analysis pipeline complete",
        extra={
            "session_id": session.session_id,
            "total_records": session.total_records,
            "total_anomalies": session.total_anomalies,
        },
    )

    return AnalyzeResponse.from_session(
        session_id=session.session_id,
        total_records=session.total_records,
        total_anomalies=session.total_anomalies,
    )
