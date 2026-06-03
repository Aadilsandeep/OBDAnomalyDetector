import { createFileRoute } from "@tanstack/react-router";
import {
  LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import {
  Activity, AlertTriangle, Database, Files, Gauge as GaugeIcon, HeartPulse, Layers, TrendingUp, TrendingDown,
} from "lucide-react";
import { Panel, PanelHeader, PanelBody, StatusDot, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import {
  healthScore, subsystems, sessionStats, healthTimeline, drivingStates, vehicleInfo,
} from "@/lib/mockData";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — AutoAssist" },
      { name: "description", content: "Vehicle health score, digital twin, telemetry timeline and session summary." },
    ],
  }),
  component: Dashboard,
});

function HealthGauge({ score }: { score: number }) {
  const r = 78;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  return (
    <div className="relative grid place-items-center">
      <svg width="200" height="200" viewBox="0 0 200 200" className="-rotate-90">
        <circle cx="100" cy="100" r={r} stroke="var(--border)" strokeWidth="14" fill="none" />
        <circle
          cx="100" cy="100" r={r}
          stroke="var(--primary)" strokeWidth="14" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={offset}
          style={{ filter: "drop-shadow(0 0 8px color-mix(in oklab, var(--primary) 50%, transparent))" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-4xl font-semibold tracking-tight text-foreground">{score}</div>
        <div className="text-xs text-muted-foreground">/ 100</div>
      </div>
    </div>
  );
}

function VehicleSilhouette() {
  return (
    <svg viewBox="0 0 360 140" className="h-32 w-full text-primary/60">
      <defs>
        <linearGradient id="bp" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <path
        d="M30 95 L70 95 L90 60 L150 50 L220 50 L255 60 L300 70 L330 78 L335 95 L310 95
           A20 20 0 0 1 270 95 L130 95 A20 20 0 0 1 90 95 Z"
        fill="url(#bp)" stroke="currentColor" strokeWidth="1.2"
      />
      <circle cx="110" cy="95" r="14" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="290" cy="95" r="14" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M155 55 L155 85 M195 55 L195 85" stroke="currentColor" strokeWidth="0.8" opacity="0.6" />
    </svg>
  );
}

function Dashboard() {
  return (
    <div>
      <PageHeader
        title="Vehicle Overview"
        description={`${vehicleInfo.name} · ${vehicleInfo.session}`}
        actions={<Badge tone="success">Live baseline</Badge>}
      />

      {/* Row 1 */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel className="lg:col-span-1">
          <PanelHeader title="Vehicle Health Score" subtitle="Composite of all subsystems" right={<Badge tone="success">Healthy</Badge>} />
          <PanelBody>
            <div className="flex flex-col items-center gap-4">
              <HealthGauge score={healthScore.score} />
              <div className="grid w-full grid-cols-2 gap-3 pt-2">
                <div className="rounded-lg border border-border bg-elevated/40 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Status</div>
                  <div className="mt-1 flex items-center gap-2 text-sm font-medium text-foreground">
                    <StatusDot status="healthy" /> Healthy
                  </div>
                </div>
                <div className="rounded-lg border border-border bg-elevated/40 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Baseline Conf.</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{healthScore.baselineConfidence}%</div>
                </div>
              </div>
            </div>
          </PanelBody>
        </Panel>

        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Vehicle Digital Twin"
            subtitle="Subsystem health overview"
            right={<Badge tone="primary">5 subsystems</Badge>}
          />
          <PanelBody>
            <div className="rounded-lg border border-border bg-elevated/30 p-4">
              <VehicleSilhouette />
            </div>
            <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {subsystems.map((s) => (
                <div key={s.name} className="flex items-center justify-between rounded-lg border border-border bg-card/60 px-3 py-2.5">
                  <div className="flex items-center gap-2.5">
                    <StatusDot status={s.status} />
                    <div className="text-sm font-medium text-foreground">{s.name}</div>
                  </div>
                  <div className="text-xs text-muted-foreground">{s.metric}</div>
                </div>
              ))}
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Row 2 */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader title="Vehicle Health Timeline" subtitle="Health · Stability · Anomaly frequency" />
          <PanelBody>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={healthTimeline} margin={{ left: -10, right: 8, top: 8 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="health" name="Health" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="stability" name="Stability" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="anomalies" name="Anomalies" stroke="var(--chart-4)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Driving States" subtitle="Time distribution this session" />
          <PanelBody>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={drivingStates} dataKey="value" nameKey="name" innerRadius={55} outerRadius={88} paddingAngle={2}>
                    {drivingStates.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Row 3 */}
      <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {sessionStats.map((s, i) => {
          const icons = [Files, Database, Layers, AlertTriangle, HeartPulse, GaugeIcon];
          const Icon = icons[i % icons.length];
          const isPositive = s.trend.startsWith("+");
          return (
            <Panel key={s.label}>
              <PanelBody className="!py-4">
                <div className="flex items-center justify-between">
                  <div className="grid h-8 w-8 place-items-center rounded-md bg-primary/12 text-primary ring-1 ring-primary/20">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className={`flex items-center gap-1 text-[11px] ${isPositive ? "text-success" : "text-muted-foreground"}`}>
                    {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {s.trend}
                  </div>
                </div>
                <div className="mt-3 text-2xl font-semibold tracking-tight text-foreground">{s.value}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{s.label}</div>
              </PanelBody>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
