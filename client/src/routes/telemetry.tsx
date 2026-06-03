import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { ChevronDown, ChevronRight, ZoomIn, ZoomOut, Crosshair } from "lucide-react";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { telemetry } from "@/lib/mockData";

export const Route = createFileRoute("/telemetry")({
  head: () => ({
    meta: [
      { title: "Telemetry Explorer — AutoAssist" },
      { name: "description", content: "Inspect raw OBD-II telemetry: RPM, speed, throttle, MAF, MAP, and more." },
    ],
  }),
  component: TelemetryPage,
});

type Series = { t: number; v: number }[];
const series: { id: string; name: string; unit: string; color: string; data: Series; default?: boolean }[] = [
  { id: "rpm", name: "RPM vs Time", unit: "rpm", color: "var(--chart-1)", data: telemetry.rpm, default: true },
  { id: "speed", name: "Speed vs Time", unit: "km/h", color: "var(--chart-2)", data: telemetry.speed, default: true },
  { id: "throttle", name: "Throttle Position vs Time", unit: "%", color: "var(--chart-3)", data: telemetry.throttle, default: true },
  { id: "maf", name: "MAF", unit: "g/s", color: "var(--chart-1)", data: telemetry.maf },
  { id: "map", name: "MAP", unit: "kPa", color: "var(--chart-5)", data: telemetry.map },
  { id: "coolant", name: "Coolant Temperature", unit: "°C", color: "var(--chart-4)", data: telemetry.coolant },
  { id: "intake", name: "Intake Air Temperature", unit: "°C", color: "var(--chart-2)", data: telemetry.intake },
  { id: "pedal", name: "Pedal Position", unit: "%", color: "var(--chart-3)", data: telemetry.pedal },
];

function Chart({ data, color, unit }: { data: Series; color: string; unit: string }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: -10, right: 8, top: 8 }}>
          <defs>
            <linearGradient id={`g-${color}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="t" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false}
                 tickFormatter={(v) => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`} />
          <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false}
                 tickFormatter={(v) => `${v}${unit ? "" : ""}`} />
          <Tooltip
            contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
            formatter={(v: number) => [`${v} ${unit}`, "Value"]}
            labelFormatter={(t) => `t = ${t}s`}
          />
          <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#g-${color})`} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function TelemetryPage() {
  const [open, setOpen] = useState<Record<string, boolean>>(
    Object.fromEntries(series.map((s) => [s.id, !!s.default])),
  );
  const [range, setRange] = useState("Full session");

  return (
    <div>
      <PageHeader
        title="Telemetry Explorer"
        description="High-resolution sensor traces from the active session"
        actions={
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-1 rounded-md border border-border bg-card px-1 py-1 sm:flex">
              {["1 min", "5 min", "15 min", "Full session"].map((r) => (
                <button key={r} onClick={() => setRange(r)}
                  className={`rounded px-2.5 py-1 text-xs ${range === r ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"}`}>
                  {r}
                </button>
              ))}
            </div>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground"><ZoomIn className="h-4 w-4" /></button>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground"><ZoomOut className="h-4 w-4" /></button>
            <button className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground"><Crosshair className="h-4 w-4" /></button>
          </div>
        }
      />

      <div className="space-y-4">
        {series.map((s) => {
          const isOpen = open[s.id];
          return (
            <Panel key={s.id}>
              <button
                onClick={() => setOpen((p) => ({ ...p, [s.id]: !p[s.id] }))}
                className="flex w-full items-center justify-between border-b border-border px-5 py-3.5 text-left"
              >
                <div className="flex items-center gap-3">
                  {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                  <div>
                    <div className="text-sm font-semibold text-foreground">{s.name}</div>
                    <div className="text-xs text-muted-foreground">Unit: {s.unit} · 1 Hz · 180 samples</div>
                  </div>
                </div>
                <Badge tone={s.default ? "primary" : "neutral"}>{s.default ? "Default" : "Expandable"}</Badge>
              </button>
              {isOpen && <PanelBody><Chart data={s.data} color={s.color} unit={s.unit} /></PanelBody>}
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
