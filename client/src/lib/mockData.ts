// Mock automotive telemetry data for AutoAssist UI

export type Status = "healthy" | "monitor" | "warning" | "critical";

export const vehicleInfo = {
  name: "2021 Honda Civic 1.5T",
  vin: "1HGFC2F59MA000000",
  session: "Session #128 · Nov 28, 2026",
  dataset: "civic_obd_session_128.csv",
  datasetStatus: "Loaded",
  analysisStatus: "Complete",
};

export const healthScore = {
  score: 87,
  status: "Healthy" as Status,
  baselineConfidence: 92,
};

export const subsystems: { name: string; status: Status; metric: string }[] = [
  { name: "Engine System", status: "healthy", metric: "RPM stable" },
  { name: "Cooling System", status: "healthy", metric: "88°C avg" },
  { name: "Airflow System", status: "monitor", metric: "MAF variance ↑" },
  { name: "Fuel System", status: "healthy", metric: "Trim nominal" },
  { name: "Electrical System", status: "healthy", metric: "13.9V" },
];

export const sessionStats = [
  { label: "Files Analyzed", value: "81", trend: "+4 vs prior" },
  { label: "Records Processed", value: "2.69M", trend: "+8.2%" },
  { label: "Operational States", value: "5", trend: "stable" },
  { label: "Detected Anomalies", value: "12", trend: "-3 vs prior" },
  { label: "Average Health Score", value: "87", trend: "+2" },
  { label: "Dominant Condition", value: "Cruising", trend: "54% time" },
];

// Health timeline (30 points)
export const healthTimeline = Array.from({ length: 30 }, (_, i) => {
  const t = i / 29;
  const health = 78 + Math.sin(t * 6) * 4 + Math.cos(t * 3) * 3 + i * 0.15;
  const stability = 70 + Math.cos(t * 4) * 8 + i * 0.1;
  const anomalies = Math.max(0, Math.round(3 + Math.sin(t * 9) * 2 + Math.random() * 1.2));
  return {
    day: `D${i + 1}`,
    health: Math.round(Math.min(100, health)),
    stability: Math.round(Math.min(100, stability)),
    anomalies,
  };
});

export const drivingStates = [
  { name: "Cruising", value: 54, color: "var(--chart-1)" },
  { name: "Traffic", value: 18, color: "var(--chart-3)" },
  { name: "Idle", value: 12, color: "var(--chart-5)" },
  { name: "Acceleration", value: 10, color: "var(--chart-2)" },
  { name: "Deceleration", value: 6, color: "var(--chart-4)" },
];

// Telemetry timeseries (180 points = 3 min @ 1Hz)
function gen(n: number, fn: (t: number, i: number) => number) {
  return Array.from({ length: n }, (_, i) => ({ t: i, v: +fn(i / n, i).toFixed(2) }));
}

export const telemetry = {
  rpm: gen(180, (t, i) => 900 + Math.max(0, Math.sin(t * 7) * 1400 + Math.sin(i * 0.3) * 250 + 600)),
  speed: gen(180, (t) => Math.max(0, 30 + Math.sin(t * 5) * 35 + Math.cos(t * 2) * 20)),
  throttle: gen(180, (t, i) => Math.max(0, Math.min(100, 22 + Math.sin(t * 8) * 28 + Math.cos(i * 0.4) * 12))),
  maf: gen(180, (t) => Math.max(2, 12 + Math.sin(t * 6) * 14 + Math.cos(t * 3) * 6)),
  map: gen(180, (t) => 35 + Math.sin(t * 4) * 22 + Math.cos(t * 2) * 8),
  coolant: gen(180, (t) => 78 + Math.sin(t * 1.5) * 6 + t * 4),
  intake: gen(180, (t) => 28 + Math.sin(t * 2) * 4 + Math.cos(t * 3) * 2),
  pedal: gen(180, (t, i) => Math.max(0, Math.min(100, 18 + Math.sin(t * 8) * 26 + Math.cos(i * 0.5) * 10))),
};

export type Severity = "Low" | "Medium" | "High" | "Critical";

export const anomalies: {
  id: string;
  time: string;
  severity: Severity;
  state: string;
  sensors: string[];
  description: string;
  factors: { name: string; weight: number }[];
}[] = [
  {
    id: "A-2041",
    time: "00:42:18",
    severity: "Medium",
    state: "Acceleration",
    sensors: ["RPM", "MAF"],
    description: "Brief MAF deviation during hard acceleration",
    factors: [
      { name: "Airflow Instability", weight: 42 },
      { name: "RPM Variability", weight: 28 },
      { name: "Throttle Deviation", weight: 18 },
      { name: "Engine Load Spike", weight: 12 },
    ],
  },
  {
    id: "A-2042",
    time: "00:58:04",
    severity: "Low",
    state: "Cruising",
    sensors: ["Coolant"],
    description: "Coolant temperature drift below baseline",
    factors: [
      { name: "Thermal Drift", weight: 55 },
      { name: "Ambient Influence", weight: 30 },
      { name: "Flow Variability", weight: 15 },
    ],
  },
  {
    id: "A-2043",
    time: "01:12:31",
    severity: "High",
    state: "Deceleration",
    sensors: ["Throttle", "RPM", "Pedal"],
    description: "Throttle-pedal correlation break under braking",
    factors: [
      { name: "Throttle Deviation", weight: 48 },
      { name: "Pedal-Throttle Lag", weight: 27 },
      { name: "RPM Variability", weight: 25 },
    ],
  },
  {
    id: "A-2044",
    time: "01:24:09",
    severity: "Critical",
    state: "Acceleration",
    sensors: ["MAP", "MAF", "RPM"],
    description: "Sustained manifold pressure spike with load mismatch",
    factors: [
      { name: "Engine Load Spike", weight: 41 },
      { name: "Manifold Pressure", weight: 33 },
      { name: "Airflow Instability", weight: 26 },
    ],
  },
  {
    id: "A-2045",
    time: "01:39:55",
    severity: "Low",
    state: "Traffic",
    sensors: ["Speed"],
    description: "Speed sensor jitter at low velocity",
    factors: [
      { name: "Sensor Jitter", weight: 70 },
      { name: "Low-Speed Noise", weight: 30 },
    ],
  },
];

// Correlation matrix
export const sensors = ["RPM", "Speed", "Throttle", "MAP", "MAF", "Coolant", "Intake", "Pedal"];
export const correlation: number[][] = [
  [1.00, 0.74, 0.81, 0.66, 0.78, 0.18, 0.22, 0.79],
  [0.74, 1.00, 0.62, 0.55, 0.60, 0.21, 0.18, 0.61],
  [0.81, 0.62, 1.00, 0.71, 0.69, 0.10, 0.14, 0.92],
  [0.66, 0.55, 0.71, 1.00, 0.83, 0.24, 0.30, 0.70],
  [0.78, 0.60, 0.69, 0.83, 1.00, 0.20, 0.27, 0.68],
  [0.18, 0.21, 0.10, 0.24, 0.20, 1.00, 0.41, 0.12],
  [0.22, 0.18, 0.14, 0.30, 0.27, 0.41, 1.00, 0.16],
  [0.79, 0.61, 0.92, 0.70, 0.68, 0.12, 0.16, 1.00],
];

// Anomaly heatmap data: sensor groups x time buckets
export const heatmapTimeBuckets = ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45"];
export const heatmapGroups = ["Engine", "Airflow", "Fuel", "Thermal", "Electrical", "Driver"];
export const heatmap: number[][] = [
  [0, 1, 0, 2, 1, 4, 2, 1],
  [0, 0, 1, 3, 0, 2, 5, 1],
  [0, 0, 0, 1, 0, 1, 0, 0],
  [1, 0, 0, 0, 2, 0, 0, 1],
  [0, 0, 0, 0, 0, 0, 1, 0],
  [0, 1, 0, 2, 0, 3, 1, 0],
];

export const severityDistribution = [
  { name: "Low", value: 5, color: "var(--success)" },
  { name: "Medium", value: 4, color: "var(--chart-1)" },
  { name: "High", value: 2, color: "var(--warning)" },
  { name: "Critical", value: 1, color: "var(--critical)" },
];

export const executiveInsights = [
  "No significant abnormalities detected across the session.",
  "Stable thermal behavior observed; coolant remained within baseline.",
  "Moderate traffic exposure during the first 18 minutes.",
  "Airflow subsystem shows mild variance — recommend monitoring over next 3 sessions.",
  "Driver behavior consistent with smooth highway cruising.",
];
