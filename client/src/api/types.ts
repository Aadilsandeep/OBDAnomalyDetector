/**
 * @file api/types.ts
 * @description TypeScript interfaces that mirror the FastAPI/Pydantic response
 * schemas. All field names use camelCase to match the backend's
 * `CamelModel` serialiser (Pydantic alias_generator = to_camel).
 *
 * ⚠  Keep in sync with server/api/schemas/*.py when the backend evolves.
 */

// ---------------------------------------------------------------------------
// POST /api/analyze
// ---------------------------------------------------------------------------

export interface AnalyzeResponse {
  /** UUID4 string identifying the newly created session. */
  sessionId: string;
  /** Always "complete" on success. */
  status: string;
  totalRecords: number;
  totalAnomalies: number;
}

// ---------------------------------------------------------------------------
// GET /api/sessions
// ---------------------------------------------------------------------------

export interface SessionListItem {
  sessionId: string;
  filename: string;
  createdAt: string;
  totalRecords: number;
  totalAnomalies: number;
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/dashboard
// ---------------------------------------------------------------------------

export interface VehicleInfo {
  name: string;
  session: string;
  dataset: string;
  datasetStatus: string;
  analysisStatus: string;
}

export interface HealthScoreData {
  score: number;
  status: string;
  riskLevel: string;
}

export interface SessionStat {
  label: string;
  value: string;
  trend: string;
}

export interface DrivingState {
  name: string;
  value: number;
  color: string;
}

export interface HealthTimelinePoint {
  index: number;
  health: number;
  anomalies: number;
}

export interface DashboardResponse {
  vehicleInfo: VehicleInfo;
  healthScore: HealthScoreData;
  sessionStats: SessionStat[];
  drivingStates: DrivingState[];
  healthTimeline: HealthTimelinePoint[];
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/anomalies
// ---------------------------------------------------------------------------

export interface AnomalyEvent {
  id: string;
  time: string;
  severity: string;
  state: string;
  sensors: string[];
  description: string;
  anomalyScore: number;
}

export interface SeverityBucket {
  name: string;
  value: number;
  color: string;
}

export interface AnomaliesResponse {
  anomalies: AnomalyEvent[];
  severityDistribution: SeverityBucket[];
  heatmapTimeBuckets: string[];
  heatmapGroups: string[];
  heatmap: number[][];
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/telemetry
// ---------------------------------------------------------------------------

export interface TelemetryPoint {
  t: number;
  v: number;
}

export interface TelemetryResponse {
  rpm: TelemetryPoint[];
  speed: TelemetryPoint[];
  maf: TelemetryPoint[];
  map: TelemetryPoint[];
  throttle: TelemetryPoint[];
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/sensors
// ---------------------------------------------------------------------------

export interface SensorPairPoint {
  x: number;
  y: number;
}

export interface SensorPair {
  id: string;
  xLabel: string;
  yLabel: string;
  correlation: number;
  data: SensorPairPoint[];
}

export interface SensorsResponse {
  sensors: string[];
  correlation: number[][];
  pairs: SensorPair[];
}

// ---------------------------------------------------------------------------
// GET /api/sessions/{session_id}/report
// ---------------------------------------------------------------------------

export interface AnomalySummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface DrivingStateSummary {
  name: string;
  percentage: number;
}

export interface ReportResponse {
  healthScore: number;
  riskLevel: string;
  anomalyRate: number;
  totalRecords: number;
  totalAnomalies: number;
  anomalySummary: AnomalySummary;
  drivingStates: DrivingStateSummary[];
  dominantState: string;
  executiveInsights: string[];
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

/** Severity tiers used across anomaly views. */
export type Severity = "Low" | "Medium" | "High" | "Critical";

/** Structured error returned by the API client on failure. */
export interface ApiError {
  status: number;
  message: string;
}
