import { createFileRoute } from "@tanstack/react-router";
import {
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { Download, FileText, Sparkles } from "lucide-react";
import { Panel, PanelHeader, PanelBody, Badge, StatusDot } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import {
  drivingStates, executiveInsights, healthScore, healthTimeline, subsystems, vehicleInfo,
} from "@/lib/mockData";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports — AutoAssist" },
      { name: "description", content: "Executive summaries and printable session reports." },
    ],
  }),
  component: ReportsPage,
});

function ReportsPage() {
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
        <Panel className="lg:col-span-2">
          <PanelHeader title="Executive Summary" subtitle="Auto-generated narrative insights"
                       right={<Badge tone="primary"><Sparkles className="h-3 w-3" /> AI insights</Badge>} />
          <PanelBody>
            <ul className="space-y-3">
              {executiveInsights.map((line, i) => (
                <li key={i} className="flex items-start gap-3 rounded-lg border border-border bg-elevated/30 px-4 py-3">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span className="text-sm text-foreground">{line}</span>
                </li>
              ))}
            </ul>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Vehicle Health Report" />
          <PanelBody>
            <dl className="space-y-3 text-sm">
              <Row k="Health Score" v={`${healthScore.score} / 100`} />
              <Row k="Baseline Confidence" v={`${healthScore.baselineConfidence}%`} />
              <Row k="Dominant Driving State" v="Cruising (54%)" />
              <Row k="Anomaly Count" v="12 (1 critical)" />
              <Row k="Session Duration" v="1h 47m" />
              <Row k="Records Processed" v="2.69M" />
            </dl>
            <div className="mt-4 rounded-lg border border-border bg-elevated/30 p-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Key findings</div>
              <ul className="mt-2 space-y-1.5 text-xs text-foreground">
                <li>• Airflow variance slightly elevated under acceleration</li>
                <li>• One critical MAP/MAF mismatch event at 01:24:09</li>
                <li>• Thermal envelope nominal across the session</li>
              </ul>
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Printable composite report */}
      <Panel className="mt-5">
        <PanelHeader title="Graphical Session Report" subtitle="Presentation-ready dashboard"
                     right={<Badge tone="neutral"><FileText className="h-3 w-3" /> Print preview</Badge>} />
        <PanelBody>
          <div className="rounded-xl border border-border bg-elevated/30 p-6">
            <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">AutoAssist Session Report</div>
                <div className="mt-1 text-xl font-semibold tracking-tight text-foreground">{vehicleInfo.name}</div>
                <div className="text-xs text-muted-foreground">{vehicleInfo.session} · VIN {vehicleInfo.vin}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Overall</div>
                <div className="text-3xl font-semibold text-primary">{healthScore.score}<span className="text-base text-muted-foreground">/100</span></div>
                <Badge tone="success">Healthy</Badge>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Health timeline</div>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={healthTimeline} margin={{ left: -20, right: 8, top: 4 }}>
                      <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" vertical={false} />
                      <XAxis dataKey="day" hide />
                      <YAxis stroke="var(--muted-foreground)" fontSize={10} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                      <Line type="monotone" dataKey="health" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="stability" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Driving states</div>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={drivingStates} dataKey="value" nameKey="name" innerRadius={40} outerRadius={68} paddingAngle={2}>
                        {drivingStates.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Legend wrapperStyle={{ fontSize: 10 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Subsystem overview</div>
                <ul className="space-y-2">
                  {subsystems.map((s) => (
                    <li key={s.name} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-foreground">
                        <StatusDot status={s.status} /> {s.name}
                      </span>
                      <span className="text-xs text-muted-foreground">{s.metric}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-lg border border-border bg-card/50 p-4">
                <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Anomaly summary</div>
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Total" value="12" />
                  <Metric label="Critical" value="1" tone="critical" />
                  <Metric label="High" value="2" tone="warning" />
                  <Metric label="Medium / Low" value="9" />
                </div>
              </div>
            </div>
          </div>
        </PanelBody>
      </Panel>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 last:border-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-medium text-foreground">{v}</dd>
    </div>
  );
}

function Metric({ label, value, tone = "primary" as "primary" | "warning" | "critical" }: { label: string; value: string; tone?: "primary" | "warning" | "critical" }) {
  const color = tone === "critical" ? "text-critical" : tone === "warning" ? "text-warning" : "text-primary";
  return (
    <div className="rounded-md border border-border bg-elevated/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${color}`}>{value}</div>
    </div>
  );
}
