import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  ScatterChart, Scatter, ResponsiveContainer, XAxis, YAxis, ZAxis, Tooltip, CartesianGrid,
} from "recharts";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { correlation, sensors, telemetry } from "@/lib/mockData";

export const Route = createFileRoute("/sensors")({
  head: () => ({
    meta: [
      { title: "Sensor Explorer — AutoAssist" },
      { name: "description", content: "Correlation heatmap and pairwise sensor relationships." },
    ],
  }),
  component: SensorPage,
});

const pairs: { id: string; x: string; y: string; xKey: keyof typeof telemetry; yKey: keyof typeof telemetry }[] = [
  { id: "rpm-speed", x: "RPM", y: "Speed", xKey: "rpm", yKey: "speed" },
  { id: "rpm-maf", x: "RPM", y: "MAF", xKey: "rpm", yKey: "maf" },
  { id: "throttle-rpm", x: "Throttle", y: "RPM", xKey: "throttle", yKey: "rpm" },
  { id: "speed-map", x: "Speed", y: "MAP", xKey: "speed", yKey: "map" },
];

function strengthLabel(v: number) {
  if (v >= 0.7) return { label: "Strong", tone: "success" as const };
  if (v >= 0.4) return { label: "Moderate", tone: "primary" as const };
  return { label: "Weak", tone: "neutral" as const };
}

function SensorPage() {
  const [pairId, setPairId] = useState(pairs[0].id);
  const pair = pairs.find((p) => p.id === pairId)!;
  const data = telemetry[pair.xKey].map((d, i) => ({ x: d.v, y: telemetry[pair.yKey][i].v }));

  return (
    <div>
      <PageHeader title="Sensor Explorer" description="Cross-sensor correlations and relationship analysis" />

      <Panel>
        <PanelHeader title="Correlation Heatmap" subtitle="Pearson correlation across primary sensors" />
        <PanelBody>
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-1 text-xs">
              <thead>
                <tr>
                  <th></th>
                  {sensors.map((s) => (
                    <th key={s} className="px-2 text-[10px] font-medium text-muted-foreground">{s}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sensors.map((rs, i) => (
                  <tr key={rs}>
                    <td className="pr-2 text-right text-[11px] font-medium text-muted-foreground">{rs}</td>
                    {correlation[i].map((v, j) => (
                      <td key={j} className="h-10 w-14 rounded-md text-center text-[11px] font-semibold"
                          style={{
                            background: `color-mix(in oklab, var(--primary) ${Math.abs(v) * 80}%, var(--elevated))`,
                            color: Math.abs(v) > 0.55 ? "var(--primary-foreground)" : "var(--foreground)",
                          }}>
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
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Pairwise Relationship"
            subtitle={`${pair.x} vs ${pair.y}`}
            right={
              <div className="flex flex-wrap gap-1">
                {pairs.map((p) => (
                  <button key={p.id} onClick={() => setPairId(p.id)}
                    className={`rounded-md px-2.5 py-1 text-[11px] ${pairId === p.id ? "bg-primary/15 text-primary ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground"}`}>
                    {p.x} × {p.y}
                  </button>
                ))}
              </div>
            }
          />
          <PanelBody>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ left: -10, right: 8, top: 8 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 4" />
                  <XAxis type="number" dataKey="x" name={pair.x} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis type="number" dataKey="y" name={pair.y} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <ZAxis range={[20, 20]} />
                  <Tooltip cursor={{ stroke: "var(--primary)", strokeWidth: 1 }}
                           contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Scatter data={data} fill="var(--primary)" fillOpacity={0.7} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Relationship Strength" subtitle="Top-ranked pair correlations" />
          <PanelBody>
            <ul className="space-y-3">
              {[
                { a: "Throttle", b: "Pedal", v: 0.92 },
                { a: "MAP", b: "MAF", v: 0.83 },
                { a: "RPM", b: "Throttle", v: 0.81 },
                { a: "RPM", b: "Pedal", v: 0.79 },
                { a: "RPM", b: "Speed", v: 0.74 },
                { a: "Coolant", b: "Intake", v: 0.41 },
                { a: "Coolant", b: "Throttle", v: 0.10 },
              ].map((r) => {
                const s = strengthLabel(r.v);
                return (
                  <li key={`${r.a}-${r.b}`}>
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground">{r.a} × {r.b}</span>
                      <Badge tone={s.tone}>{s.label} · {r.v.toFixed(2)}</Badge>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-elevated">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${r.v * 100}%` }} />
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
