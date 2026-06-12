/**
 * @file routes/sensors.tsx
 * @description Sensor Explorer page — correlation heatmap and pairwise
 * sensor scatter plots.
 *
 * Data source: `GET /api/sessions/{session_id}/sensors` via `useSensors()`.
 *
 * Schema notes:
 * - `SensorsResponse.pairs` provides pre-computed pairwise data from the backend.
 *   Replaces the hardcoded `pairs` array and inline scatter data construction.
 * - Relationship strength ranking is derived from the correlation matrix.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  ResponsiveContainer,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui-kit/StateViews";
import { useSensors } from "@/hooks/useSensors";
import { useSessionStore } from "@/lib/sessionStore";
import type { SensorPair } from "@/api/types";

export const Route = createFileRoute("/sensors")({
  head: () => ({
    meta: [
      { title: "Sensor Explorer — AutoAssist" },
      {
        name: "description",
        content: "Correlation heatmap and pairwise sensor relationships.",
      },
    ],
  }),
  component: SensorPage,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function strengthLabel(v: number): { label: string; tone: "success" | "primary" | "neutral" } {
  if (v >= 0.7) return { label: "Strong", tone: "success" };
  if (v >= 0.4) return { label: "Moderate", tone: "primary" };
  return { label: "Weak", tone: "neutral" };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function SensorPage() {
  const { sessionId } = useSessionStore();
  const { data, isLoading, isError, error, refetch } = useSensors();
  const [pairId, setPairId] = useState<string | null>(null);

  // -- No session -----------------------------------------------------------
  if (!sessionId) {
    return (
      <div>
        <PageHeader title="Sensor Explorer" description="Upload an OBD-II CSV to begin" />
        <EmptyState />
      </div>
    );
  }

  // -- Loading ---------------------------------------------------------------
  if (isLoading) {
    return (
      <div>
        <PageHeader title="Sensor Explorer" description="Loading sensor correlation data…" />
        <LoadingState label="Fetching correlation matrix…" />
      </div>
    );
  }

  // -- Error ----------------------------------------------------------------
  if (isError || !data) {
    return (
      <div>
        <PageHeader title="Sensor Explorer" />
        <ErrorState
          message={error?.message ?? "Failed to load sensor data."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const { sensors, correlation, pairs } = data;

  // Resolve active pair
  const resolvedPairId = pairId ?? pairs[0]?.id ?? null;
  const pair: SensorPair | undefined = pairs.find((p) => p.id === resolvedPairId);

  // Top correlation pairs derived from matrix for the ranking panel
  const topPairs = useMemo(() => {
    const ranked: { a: string; b: string; v: number }[] = [];
    for (let i = 0; i < sensors.length; i++) {
      for (let j = i + 1; j < sensors.length; j++) {
        ranked.push({ a: sensors[i], b: sensors[j], v: correlation[i][j] });
      }
    }
    return ranked.sort((x, y) => Math.abs(y.v) - Math.abs(x.v)).slice(0, 7);
  }, [sensors, correlation]);

  return (
    <div>
      <PageHeader title="Sensor Explorer" description="Cross-sensor correlations and relationship analysis" />

      {/* Correlation Heatmap */}
      <Panel>
        <PanelHeader
          title="Correlation Heatmap"
          subtitle="Pearson correlation across primary sensors"
        />
        <PanelBody>
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-1 text-xs">
              <thead>
                <tr>
                  <th />
                  {sensors.map((s) => (
                    <th key={s} className="px-2 text-[10px] font-medium text-muted-foreground">
                      {s}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sensors.map((rs, i) => (
                  <tr key={rs}>
                    <td className="pr-2 text-right text-[11px] font-medium text-muted-foreground">
                      {rs}
                    </td>
                    {correlation[i].map((v, j) => (
                      <td
                        key={j}
                        className="h-10 w-14 rounded-md text-center text-[11px] font-semibold"
                        style={{
                          background: `color-mix(in oklab, var(--primary) ${Math.abs(v) * 80}%, var(--elevated))`,
                          color:
                            Math.abs(v) > 0.55
                              ? "var(--primary-foreground)"
                              : "var(--foreground)",
                        }}
                      >
                        {v.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PanelBody>
      </Panel>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Pairwise Scatter */}
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Pairwise Relationship"
            subtitle={pair ? `${pair.xLabel} vs ${pair.yLabel}` : "Select a pair"}
            right={
              <div className="flex flex-wrap gap-1">
                {pairs.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPairId(p.id)}
                    className={`rounded-md px-2.5 py-1 text-[11px] ${resolvedPairId === p.id ? "bg-primary/15 text-primary ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground"}`}
                  >
                    {p.xLabel} × {p.yLabel}
                  </button>
                ))}
              </div>
            }
          />
          <PanelBody>
            {pair && pair.data.length > 0 ? (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ left: -10, right: 8, top: 8 }}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name={pair.xLabel}
                      stroke="var(--muted-foreground)"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name={pair.yLabel}
                      stroke="var(--muted-foreground)"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                    />
                    <ZAxis range={[20, 20]} />
                    <Tooltip
                      cursor={{ stroke: "var(--primary)", strokeWidth: 1 }}
                      contentStyle={{
                        background: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Scatter data={pair.data} fill="var(--primary)" fillOpacity={0.7} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No pair data available.</p>
            )}
          </PanelBody>
        </Panel>

        {/* Relationship Strength ranking */}
        <Panel>
          <PanelHeader
            title="Relationship Strength"
            subtitle="Top-ranked pair correlations"
          />
          <PanelBody>
            <ul className="space-y-3">
              {topPairs.map((r) => {
                const s = strengthLabel(Math.abs(r.v));
                return (
                  <li key={`${r.a}-${r.b}`}>
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground">
                        {r.a} × {r.b}
                      </span>
                      <Badge tone={s.tone}>
                        {s.label} · {Math.abs(r.v).toFixed(2)}
                      </Badge>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-elevated">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.abs(r.v) * 100}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </PanelBody>
        </Panel>
      </div>
    </div>
  );
}
