import { createFileRoute } from "@tanstack/react-router";
import { Cpu, Database, Palette, Radio, Wrench, Truck } from "lucide-react";
import { Panel, PanelHeader, PanelBody, Badge } from "@/components/ui-kit/Card";
import { PageHeader } from "@/components/layout/AppLayout";
import { vehicleInfo } from "@/lib/mockData";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — AutoAssist" },
      { name: "description", content: "Theme, dataset and system information for AutoAssist." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <div>
      <PageHeader title="Settings" description="Workspace preferences and integrations" />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Theme" subtitle="Visual appearance" right={<Palette className="h-4 w-4 text-muted-foreground" />} />
          <PanelBody>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border-2 border-primary bg-elevated p-4">
                <div className="mb-2 h-12 rounded-md bg-background" />
                <div className="text-sm font-medium text-foreground">Dark Automotive</div>
                <div className="text-xs text-muted-foreground">Default · active</div>
              </div>
              <div className="rounded-lg border border-border bg-card/50 p-4 opacity-60">
                <div className="mb-2 h-12 rounded-md bg-elevated" />
                <div className="text-sm font-medium text-foreground">Light</div>
                <div className="text-xs text-muted-foreground">Coming soon</div>
              </div>
            </div>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Dataset Information" subtitle="Active analysis dataset" right={<Database className="h-4 w-4 text-muted-foreground" />} />
          <PanelBody>
            <dl className="space-y-2 text-sm">
              <Row k="Source file" v={vehicleInfo.dataset} />
              <Row k="Records" v="2,694,108" />
              <Row k="Sample rate" v="1 Hz" />
              <Row k="Duration" v="1h 47m 22s" />
              <Row k="Sensors captured" v="14" />
              <Row k="Status" v={vehicleInfo.datasetStatus} />
            </dl>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="System Information" right={<Cpu className="h-4 w-4 text-muted-foreground" />} />
          <PanelBody>
            <dl className="space-y-2 text-sm">
              <Row k="Application" v="AutoAssist" />
              <Row k="Version" v="2.4.1 · build 2611" />
              <Row k="Engine" v="AutoAssist Analytics Core" />
              <Row k="Baseline model" v="Universal v3 · 2026.10" />
              <Row k="Last sync" v="3 min ago" />
            </dl>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Future Integrations" subtitle="On the roadmap" />
          <PanelBody>
            <ul className="space-y-2">
              {[
                { icon: Radio, name: "Live OBD-II Support", desc: "Stream real-time vehicle telemetry over Bluetooth/Wi-Fi" },
                { icon: Wrench, name: "Predictive Maintenance", desc: "Forecast component wear from behavioral drift" },
                { icon: Truck, name: "Fleet Analytics", desc: "Aggregate health across multiple vehicles" },
              ].map(({ icon: Icon, name, desc }) => (
                <li key={name} className="flex items-start gap-3 rounded-lg border border-border bg-elevated/30 px-4 py-3">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary/12 text-primary ring-1 ring-primary/20">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium text-foreground">{name}</div>
                      <Badge tone="neutral">Coming soon</Badge>
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{desc}</div>
                  </div>
                </li>
              ))}
            </ul>
          </PanelBody>
        </Panel>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-1.5 last:border-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-medium text-foreground">{v}</dd>
    </div>
  );
}
