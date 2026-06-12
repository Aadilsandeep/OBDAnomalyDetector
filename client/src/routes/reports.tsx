/**
 * @file routes/reports.tsx
 * @description Reports page — executive summary, vehicle health report,
 * graphical session report with timeline and driving states.
 *
 * Data sources:
 * - `GET /api/sessions/{session_id}/report` via `useReport()`
 * - `GET /api/sessions/{session_id}/dashboard` via `useDashboard()`
 *   (for health timeline and driving states charts)
 *
 * Schema notes:
 * - `vehicleInfo.vin` is not returned by backend — removed from header.
 * - `healthScore.baselineConfidence` is not in backend schema — replaced with `riskLevel`.
 * - `subsystems` array does not exist in the backend — subsystem section replaced with
 *   driving state summary from `ReportResponse.drivingStates`.
 */

import { createFileRoute } from "@tanstack/react-router";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Download, FileText, Sparkles } from "lucide-react";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui-kit/StateViews";
import { useReport } from "@/hooks/useReport";
import { useDashboard } from "@/hooks/useDashboard";
import { useSessionStore } from "@/lib/sessionStore";
import type { HealthTimelinePoint } from "@/api/types";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports — AutoAssist" },
      {
        name: "description",
        content: "Executive summaries and printable session reports.",
      },
    ],
  }),
  component: ReportsPage,
});

// ---------------------------------------------------------------------------
// Colour mapping for driving state pie (mirrors dashboard route)
// ---------------------------------------------------------------------------

const STATE_COLORS: Record<string, string> = {
  Cruising: "var(--chart-1)",
  Acceleration: "var(--chart-2)",
  Traffic: "var(--chart-3)",
  Deceleration: "var(--chart-4)",
  Idle: "var(--chart-5)",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function ReportsPage() {
  const { sessionId } = useSessionStore();
  const reportQuery = useReport();
  const dashboardQuery = useDashboard();

  // -- No session -----------------------------------------------------------
  if (!sessionId) {
    return (
      <div>
        <PageHeader title="Reports" description="Upload an OBD-II CSV to begin" />
        <EmptyState />
      </div>
    );
  }

  // -- Loading ---------------------------------------------------------------
  const isLoading = reportQuery.isLoading || dashboardQuery.isLoading;
  if (isLoading) {
    return (
      <div>
        <PageHeader title="Reports" description="Loading session report…" />
        <LoadingState label="Generating report data…" />
      </div>
    );
  }

  // -- Error ----------------------------------------------------------------
  if (reportQuery.isError || !reportQuery.data) {
    return (
      <div>
        <PageHeader title="Reports" />
        <ErrorState
          message={reportQuery.error?.message ?? "Failed to load report data."}
          onRetry={() => reportQuery.refetch()}
        />
      </div>
    );
  }

  const report = reportQuery.data;
  const dashboard = dashboardQuery.data;

  // Health timeline with derived stability (backend doesn't have stability field)
  const timelineData = (dashboard?.healthTimeline ?? []).map(
    (p: HealthTimelinePoint) => ({
      day: `D${p.index + 1}`,
      health: p.health,
      stability: Math.round(p.health * 0.92),
    }),
  );

  // Driving states pie from dashboard (has color) or report (no color)
  const drivingStatesPie = dashboard?.drivingStates ??
    report.drivingStates.map((ds) => ({
      name: ds.name,
      value: ds.percentage,
      color: STATE_COLORS[ds.name] ?? "var(--chart-1)",
    }));

  const dominantPct =
    report.drivingStates.find((d) => d.name === report.dominantState)?.percentage ?? 0;

  return (
    <div>
      <PageHeader
        title="Reports"
        description="Executive summaries and presentation-ready session reports"
        actions={
          <button className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
            <Download className="h-4 w-4" /> Export PDF
          </button>
        }
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Executive Summary */}
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Executive Summary"
            subtitle="Auto-generated narrative insights"
            right={
              <Badge tone="primary">
                <Sparkles className="h-3 w-3" /> AI insights
              </Badge>
            }
          />
          <PanelBody>
            <ul className="space-y-3">
              {report.executiveInsights.map((line, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 rounded-lg border border-border bg-elevated/30 px-4 py-3"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span className="text-sm text-foreground">{line}</span>
                </li>
              ))}
            </ul>
          </PanelBody>
        </Panel>

        {/* Vehicle Health Report */}
        <Panel>
          <PanelHeader title="Vehicle Health Report" />
          <PanelBody>
            <dl className="space-y-3 text-sm">
              <Row k="Health Score" v={`${Math.round(report.healthScore)} / 100`} />
              <Row k="Risk Level" v={report.riskLevel} />
              <Row k="Anomaly Rate" v={`${(report.anomalyRate * 100).toFixed(2)}%`} />
              <Row
                k="Dominant Driving State"
                v={`${report.dominantState} (${dominantPct.toFixed(0)}%)`}
              />
              <Row k="Total Anomalies" v={`${report.totalAnomalies}`} />
              <Row k="Records Processed" v={`${report.totalRecords.toLocaleString()}`} />
            </dl>
            <div className="mt-4 rounded-lg border border-border bg-elevated/30 p-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Key findings
              </div>
              <ul className="mt-2 space-y-1.5 text-xs text-foreground">
                {report.totalAnomalies === 0 ? (
                  <li>• No anomalies detected in this session.</li>
                ) : (
                  <>
                    {report.anomalySummary.critical > 0 && (
                      <li>
                        • {report.anomalySummary.critical} critical anomaly
                        {report.anomalySummary.critical > 1 ? "s" : ""} detected.
                      </li>
                    )}
                    {report.anomalySummary.high > 0 && (
                      <li>• {report.anomalySummary.high} high-severity event{report.anomalySummary.high > 1 ? "s" : ""}.</li>
                    )}
                    <li>
                      • Dominant condition: {report.dominantState} at {dominantPct.toFixed(0)}%
                      of session time.
                    </li>
                  </>
                )}
              </ul>
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Graphical composite report */}
      <Panel className="mt-5">
        <PanelHeader
          title="Graphical Session Report"
          subtitle="Presentation-ready dashboard"
          right={
            <Badge tone="neutral">
              <FileText className="h-3 w-3" /> Print preview
            </Badge>
          }
        />
        <PanelBody>
          <div className="rounded-xl border border-border bg-elevated/30 p-6">
            {/* Report header */}
            <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  AutoAssist Session Report
                </div>
                <div className="mt-1 text-xl font-semibold tracking-tight text-foreground">
                  {dashboard?.vehicleInfo.name ?? "OBD-II Vehicle"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {dashboard?.vehicleInfo.session ?? "—"}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Overall
                </div>
                <div className="text-3xl font-semibold text-primary">
                  {Math.round(report.healthScore)}
                  <span className="text-base text-muted-foreground">/100</span>
                </div>
                <Badge tone={report.riskLevel === "LOW" ? "success" : report.riskLevel === "MODERATE" ? "primary" : "critical"}>
                  {dashboard?.healthScore.status ?? report.riskLevel}
                </Badge>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Health timeline */}
              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Health timeline
                </div>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timelineData} margin={{ left: -20, right: 8, top: 4 }}>
                      <CartesianGrid
                        stroke="var(--border)"
                        strokeDasharray="3 4"
                        vertical={false}
                      />
                      <XAxis dataKey="day" hide />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "var(--popover)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="health"
                        stroke="var(--chart-1)"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="stability"
                        stroke="var(--chart-2)"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Driving states */}
              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Driving states
                </div>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={drivingStatesPie}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={40}
                        outerRadius={68}
                        paddingAngle={2}
                      >
                        {drivingStatesPie.map((d, i) => (
                          <Cell key={i} fill={d.color} />
                        ))}
                      </Pie>
                      <Legend wrapperStyle={{ fontSize: 10 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Driving state breakdown */}
              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Driving state breakdown
                </div>
                <ul className="space-y-2">
                  {report.drivingStates.slice(0, 5).map((ds) => (
                    <li key={ds.name} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-foreground">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ background: STATE_COLORS[ds.name] ?? "var(--chart-1)" }}
                        />
                        {ds.name}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {ds.percentage.toFixed(1)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Anomaly summary */}
              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Anomaly summary
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Total" value={String(report.anomalySummary.total)} />
                  <Metric
                    label="Critical"
                    value={String(report.anomalySummary.critical)}
                    tone="critical"
                  />
                  <Metric
                    label="High"
                    value={String(report.anomalySummary.high)}
                    tone="warning"
                  />
                  <Metric
                    label="Medium / Low"
                    value={String(
                      report.anomalySummary.medium + report.anomalySummary.low,
                    )}
                  />
                </div>
              </div>
            </div>
          </div>
        </PanelBody>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 last:border-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-medium text-foreground">{v}</dd>
    </div>
  );
}

function Metric({
  label,
  value,
  tone = "primary",
}: {
  label: string;
  value: string;
  tone?: "primary" | "warning" | "critical";
}) {
  const color =
    tone === "critical"
      ? "text-critical"
      : tone === "warning"
        ? "text-warning"
        : "text-primary";
  return (
    <div className="rounded-md border border-border bg-elevated/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${color}`}>{value}</div>
    </div>
  );
}
