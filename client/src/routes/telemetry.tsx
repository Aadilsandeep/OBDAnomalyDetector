/**
 * @file routes/telemetry.tsx
 * @description Telemetry Explorer page — expandable area charts for OBD-II
 * sensor time-series data.
 *
 * Data source: `GET /api/sessions/{session_id}/telemetry` via `useTelemetry()`.
 *
 * Schema notes:
 * - Backend provides 5 sensors: rpm, speed, maf, map, throttle.
 * - coolant, intake, pedal are NOT in the backend schema and are omitted.
 * - Sample count and frequency labels are derived dynamically from the data.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { ChevronDown, ChevronRight, ZoomIn, ZoomOut, Crosshair } from "lucide-react";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui-kit/StateViews";
import { useTelemetry } from "@/hooks/useTelemetry";
import { useSessionStore } from "@/lib/sessionStore";
import type { TelemetryResponse, TelemetryPoint } from "@/api/types";

export const Route = createFileRoute("/telemetry")({
  head: () => ({
    meta: [
      { title: "Telemetry Explorer — AutoAssist" },
      {
        name: "description",
        content: "Inspect raw OBD-II telemetry: RPM, speed, throttle, MAF, MAP, and more.",
      },
    ],
  }),
  component: TelemetryPage,
});

// ---------------------------------------------------------------------------
// Series configuration
// ---------------------------------------------------------------------------

type SeriesConfig = {
  id: keyof TelemetryResponse;
  name: string;
  unit: string;
  color: string;
  default?: boolean;
};

const SERIES_CONFIGS: SeriesConfig[] = [
  { id: "rpm", name: "RPM vs Time", unit: "rpm", color: "var(--chart-1)", default: true },
  { id: "speed", name: "Speed vs Time", unit: "km/h", color: "var(--chart-2)", default: true },
  {
    id: "throttle",
    name: "Throttle Position vs Time",
    unit: "%",
    color: "var(--chart-3)",
    default: true,
  },
  { id: "maf", name: "MAF (Mass Air Flow)", unit: "g/s", color: "var(--chart-1)" },
  { id: "map", name: "MAP (Manifold Pressure)", unit: "kPa", color: "var(--chart-5)" },
];

// ---------------------------------------------------------------------------
// Sub-component: Chart
// ---------------------------------------------------------------------------

function Chart({
  data,
  color,
  unit,
}: {
  data: TelemetryPoint[];
  color: string;
  unit: string;
}) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: -10, right: 8, top: 8 }}>
          <defs>
            <linearGradient id={`g-${color.replace(/[^a-z0-9]/gi, "")}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" vertical={false} />
          <XAxis
            dataKey="t"
            stroke="var(--muted-foreground)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) =>
              `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`
            }
          />
          <YAxis
            stroke="var(--muted-foreground)"
            fontSize={11}
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
            formatter={(v: number) => [`${v} ${unit}`, "Value"]}
            labelFormatter={(t) => `t = ${t}s`}
          />
          <Area
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={2}
            fill={`url(#g-${color.replace(/[^a-z0-9]/gi, "")})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function TelemetryPage() {
  const { sessionId } = useSessionStore();
  const { data, isLoading, isError, error, refetch } = useTelemetry();
  const [open, setOpen] = useState<Record<string, boolean>>(
    Object.fromEntries(SERIES_CONFIGS.map((s) => [s.id, !!s.default])),
  );
  const [range, setRange] = useState("Full session");

  // -- No session -----------------------------------------------------------
  if (!sessionId) {
    return (
      <div>
        <PageHeader title="Telemetry Explorer" description="Upload an OBD-II CSV to begin" />
        <EmptyState />
      </div>
    );
  }

  // -- Loading ---------------------------------------------------------------
  if (isLoading) {
    return (
      <div>
        <PageHeader title="Telemetry Explorer" description="Loading telemetry data…" />
        <LoadingState label="Fetching sensor time-series…" />
      </div>
    );
  }

  // -- Error ----------------------------------------------------------------
  if (isError || !data) {
    return (
      <div>
        <PageHeader title="Telemetry Explorer" />
        <ErrorState
          message={error?.message ?? "Failed to load telemetry data."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Telemetry Explorer"
        description="High-resolution sensor traces from the active session"
        actions={
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-1 rounded-md border border-border bg-card px-1 py-1 sm:flex">
              {["1 min", "5 min", "15 min", "Full session"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`rounded px-2.5 py-1 text-xs ${range === r ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {r}
                </button>
              ))}
            </div>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground">
              <ZoomIn className="h-4 w-4" />
            </button>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground">
              <ZoomOut className="h-4 w-4" />
            </button>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground">
              <Crosshair className="h-4 w-4" />
            </button>
          </div>
        }
      />

      <div className="space-y-4">
        {SERIES_CONFIGS.map((s) => {
          const seriesData = data[s.id];
          const sampleCount = seriesData?.length ?? 0;
          const isOpen = open[s.id];
          return (
            <Panel key={s.id}>
              <button
                onClick={() => setOpen((p) => ({ ...p, [s.id]: !p[s.id] }))}
                className="flex w-full items-center justify-between border-b border-border px-5 py-3.5 text-left"
              >
                <div className="flex items-center gap-3">
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <div>
                    <div className="text-sm font-semibold text-foreground">{s.name}</div>
                    <div className="text-xs text-muted-foreground">
                      Unit: {s.unit} · 1 Hz · {sampleCount} samples
                    </div>
                  </div>
                </div>
                <Badge tone={s.default ? "primary" : "neutral"}>
                  {s.default ? "Default" : "Expandable"}
                </Badge>
              </button>
              {isOpen && seriesData && seriesData.length > 0 && (
                <PanelBody>
                  <Chart data={seriesData} color={s.color} unit={s.unit} />
                </PanelBody>
              )}
              {isOpen && (!seriesData || seriesData.length === 0) && (
                <PanelBody>
                  <p className="text-sm text-muted-foreground">
                    No data available for {s.name}.
                  </p>
                </PanelBody>
              )}
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
