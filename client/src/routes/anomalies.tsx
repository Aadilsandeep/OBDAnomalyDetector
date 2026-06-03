import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
} from "recharts";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import {
  anomalies, heatmap, heatmapGroups, heatmapTimeBuckets, severityDistribution, type Severity,
} from "@/lib/mockData";
import { AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/anomalies")({
  head: () => ({
    meta: [
      { title: "Anomaly Center — AutoAssist" },
      { name: "description", content: "Investigate anomalies, severities and contributing factors across the session." },
    ],
  }),
  component: AnomalyPage,
});

const sevTone: Record<Severity, "neutral" | "success" | "warning" | "critical" | "primary"> = {
  Low: "success", Medium: "primary", High: "warning", Critical: "critical",
};

function AnomalyPage() {
  const [selectedId, setSelectedId] = useState(anomalies[3].id);
  const selected = anomalies.find((a) => a.id === selectedId)!;
  const maxHeat = Math.max(...heatmap.flat(), 1);

  return (
    <div>
      <PageHeader
        title="Anomaly Center"
        description="Severity, distribution and contributing factor analysis"
        actions={<Badge tone="warning"><AlertTriangle className="h-3 w-3" /> 12 detected</Badge>}
      />

      {/* Timeline */}
      <Panel>
        <PanelHeader title="Anomaly Timeline" subtitle="Click an event to inspect details" />
        <PanelBody>
          <div className="relative">
            <div className="h-px w-full bg-border" />
            <div className="mt-2 grid grid-cols-12 text-[10px] text-muted-foreground">
              {Array.from({ length: 12 }).map((_, i) => <div key={i}>{`00:${(i * 10).toString().padStart(2, "0")}`}</div>)}
            </div>
            <div className="relative mt-3 h-16">
              {anomalies.map((a, i) => {
                const positions = [8, 22, 44, 60, 78];
                const pos = positions[i % positions.length];
                const tone = a.severity === "Critical" ? "var(--critical)" :
                             a.severity === "High" ? "var(--warning)" :
                             a.severity === "Medium" ? "var(--primary)" : "var(--success)";
                const active = a.id === selectedId;
                return (
                  <button
                    key={a.id}
                    onClick={() => setSelectedId(a.id)}
                    style={{ left: `${pos}%`, backgroundColor: tone, boxShadow: active ? `0 0 0 4px color-mix(in oklab, ${tone} 30%, transparent)` : undefined }}
                    className={`absolute top-1 h-4 w-4 -translate-x-1/2 rounded-full ring-2 ring-background transition-transform hover:scale-125 ${active ? "scale-125" : ""}`}
                    title={`${a.id} · ${a.severity}`}
                  />
                );
              })}
            </div>
          </div>
        </PanelBody>
      </Panel>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Heatmap */}
        <Panel className="lg:col-span-2">
          <PanelHeader title="Anomaly Heatmap" subtitle="Concentration across sensor groups and time" />
          <PanelBody>
            <div className="overflow-x-auto">
              <table className="w-full border-separate border-spacing-1 text-xs">
                <thead>
                  <tr>
                    <th></th>
                    {heatmapTimeBuckets.map((t) => (
                      <th key={t} className="px-1 text-[10px] font-medium text-muted-foreground">{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapGroups.map((g, i) => (
                    <tr key={g}>
                      <td className="pr-2 text-right text-[11px] font-medium text-muted-foreground">{g}</td>
                      {heatmap[i].map((v, j) => {
                        const intensity = v / maxHeat;
                        return (
                          <td key={j} className="h-9 min-w-10 rounded-md text-center text-[10px] font-semibold text-foreground"
                              style={{
                                background: `color-mix(in oklab, var(--primary) ${intensity * 70}%, var(--elevated))`,
                                color: intensity > 0.5 ? "var(--primary-foreground)" : "var(--muted-foreground)",
                              }}>
                            {v > 0 ? v : ""}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center gap-3 text-[11px] text-muted-foreground">
              <span>Low</span>
              <div className="h-2 w-40 rounded" style={{ background: "linear-gradient(90deg, var(--elevated), var(--primary))" }} />
              <span>High</span>
            </div>
          </PanelBody>
        </Panel>

        {/* Severity */}
        <Panel>
          <PanelHeader title="Severity Distribution" />
          <PanelBody>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={severityDistribution} margin={{ left: -20, right: 8 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {severityDistribution.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              {severityDistribution.map((s) => (
                <div key={s.name} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
                  <span className="text-muted-foreground">{s.name}</span>
                  <span className="ml-auto font-medium text-foreground">{s.value}</span>
                </div>
              ))}
            </div>
          </PanelBody>
        </Panel>
      </div>

      {/* Detail + Contributing factors */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader
            title={`Anomaly ${selected.id}`}
            subtitle={`${selected.time} · ${selected.state}`}
            right={<Badge tone={sevTone[selected.severity]}>{selected.severity}</Badge>}
          />
          <PanelBody>
            <p className="text-sm text-foreground">{selected.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {selected.sensors.map((s) => <Badge key={s} tone="primary">{s}</Badge>)}
            </div>
            <div className="mt-5">
              <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">All anomalies</div>
              <div className="overflow-hidden rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-elevated/40 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">ID</th>
                      <th className="px-3 py-2 text-left font-medium">Time</th>
                      <th className="px-3 py-2 text-left font-medium">Severity</th>
                      <th className="px-3 py-2 text-left font-medium">State</th>
                      <th className="px-3 py-2 text-left font-medium">Sensors</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.map((a) => (
                      <tr key={a.id}
                          onClick={() => setSelectedId(a.id)}
                          className={`cursor-pointer border-t border-border hover:bg-elevated/40 ${a.id === selectedId ? "bg-primary/5" : ""}`}>
                        <td className="px-3 py-2 font-mono text-xs text-foreground">{a.id}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.time}</td>
                        <td className="px-3 py-2"><Badge tone={sevTone[a.severity]}>{a.severity}</Badge></td>
                        <td className="px-3 py-2 text-muted-foreground">{a.state}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.sensors.join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Contributing Factors" subtitle="Per-factor contribution to anomaly score" />
          <PanelBody>
            <div className="space-y-4">
              {selected.factors.map((f) => (
                <div key={f.name}>
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground">{f.name}</span>
                    <span className="text-muted-foreground">{f.weight}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-elevated">
                    <div className="h-full rounded-full bg-primary"
                         style={{ width: `${f.weight}%`, boxShadow: "0 0 8px color-mix(in oklab, var(--primary) 60%, transparent)" }} />
                  </div>
                </div>
              ))}
            </div>
          </PanelBody>
        </Panel>
      </div>
    </div>
  );
}
