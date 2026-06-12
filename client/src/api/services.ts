/**
 * @file api/services.ts
 * @description Typed service functions for every FastAPI backend endpoint.
 *
 * Each function corresponds 1-to-1 with a backend route, accepts only the
 * parameters that route requires, and returns a fully-typed Promise.
 *
 * All functions use the `apiFetch` base client which handles:
 * - Base URL resolution
 * - Non-2xx error handling via `ApiClientError`
 * - Network failure wrapping
 *
 * @example
 * ```ts
 * const response = await postAnalyze(file);
 * const dashboard = await getDashboard(response.sessionId);
 * ```
 */

import { apiFetch } from "./client";
import type {
  AnalyzeResponse,
  AnomaliesResponse,
  DashboardResponse,
  ReportResponse,
  SensorsResponse,
  SessionListItem,
  TelemetryResponse,
} from "./types";

// ---------------------------------------------------------------------------
// POST /api/analyze
// ---------------------------------------------------------------------------

/**
 * Upload an OBD-II CSV file and run the full ML analysis pipeline.
 *
 * @param file - CSV `File` object from an `<input type="file">` or drag-drop.
 * @returns `AnalyzeResponse` containing the new `sessionId`.
 * @throws `ApiClientError` on validation failure (400/422) or server error (500).
 */
export async function postAnalyze(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  return apiFetch<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    body: formData,
  });
}

// ---------------------------------------------------------------------------
// GET /api/sessions
// ---------------------------------------------------------------------------

/**
 * List all active analysis sessions held in the backend's in-memory store.
 *
 * @returns Array of session summary objects.
 */
export async function getSessions(): Promise<SessionListItem[]> {
  return apiFetch<SessionListItem[]>("/api/sessions");
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/dashboard
// ---------------------------------------------------------------------------

/**
 * Fetch composite dashboard data for a session.
 *
 * @param sessionId - UUID returned by `postAnalyze`.
 * @returns `DashboardResponse` with vehicle info, health score, stats, and charts.
 * @throws `ApiClientError` with status 404 if the session is not found.
 */
export async function getDashboard(
  sessionId: string,
): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>(
    `/api/sessions/${sessionId}/dashboard`,
  );
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/anomalies
// ---------------------------------------------------------------------------

/**
 * Fetch anomaly data for a session.
 *
 * @param sessionId - UUID returned by `postAnalyze`.
 * @returns `AnomaliesResponse` with event list, severity distribution, and heatmap.
 */
export async function getAnomalies(
  sessionId: string,
): Promise<AnomaliesResponse> {
  return apiFetch<AnomaliesResponse>(
    `/api/sessions/${sessionId}/anomalies`,
  );
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/telemetry
// ---------------------------------------------------------------------------

/**
 * Fetch sensor time-series telemetry for a session.
 *
 * Backend returns: rpm, speed, maf, map, throttle (5 sensors).
 *
 * @param sessionId - UUID returned by `postAnalyze`.
 * @returns `TelemetryResponse` with arrays of `{t, v}` data points per sensor.
 */
export async function getTelemetry(
  sessionId: string,
): Promise<TelemetryResponse> {
  return apiFetch<TelemetryResponse>(
    `/api/sessions/${sessionId}/telemetry`,
  );
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/sensors
// ---------------------------------------------------------------------------

/**
 * Fetch correlation matrix and pairwise sensor data for a session.
 *
 * @param sessionId - UUID returned by `postAnalyze`.
 * @returns `SensorsResponse` with sensor labels, NxN matrix, and scatter pairs.
 */
export async function getSensors(
  sessionId: string,
): Promise<SensorsResponse> {
  return apiFetch<SensorsResponse>(
    `/api/sessions/${sessionId}/sensors`,
  );
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/report
// ---------------------------------------------------------------------------

/**
 * Fetch the executive session report for a session.
 *
 * @param sessionId - UUID returned by `postAnalyze`.
 * @returns `ReportResponse` with health summary, anomaly breakdown, and insights.
 */
export async function getReport(sessionId: string): Promise<ReportResponse> {
  return apiFetch<ReportResponse>(`/api/sessions/${sessionId}/report`);
}
