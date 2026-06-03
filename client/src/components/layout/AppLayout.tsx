import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Activity,
  AlertTriangle,
  Gauge,
  FileText,
  Settings as SettingsIcon,
  Car,
  Database,
  CircleDot,
  Menu,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { vehicleInfo } from "@/lib/mockData";

const nav: { to: string; label: string; icon: typeof LayoutDashboard; exact?: boolean }[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/telemetry", label: "Telemetry Explorer", icon: Activity },
  { to: "/anomalies", label: "Anomaly Center", icon: AlertTriangle },
  { to: "/sensors", label: "Sensor Explorer", icon: Gauge },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/30">
        <Car className="h-5 w-5" />
      </div>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight text-foreground">AutoAssist</div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Vehicle Intelligence</div>
      </div>
    </div>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-sidebar">
      <div className="px-5 py-5">
        <Logo />
      </div>
      <nav className="flex-1 px-3">
        <div className="px-2 pb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Workspace
        </div>
        <ul className="space-y-1">
          {nav.map((item) => {
            const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <li key={item.to}>
                <Link
                  to={item.to as any}
                  onClick={onNavigate}
                  className={`group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-primary/12 text-primary ring-1 ring-primary/25"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`} />
                  <span className="font-medium">{item.label}</span>
                  {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="m-3 rounded-lg border border-border bg-card/60 p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CircleDot className="h-3.5 w-3.5 text-success" />
          Analyzer online
        </div>
        <div className="mt-1 text-xs text-muted-foreground">v2.4.1 · build 2611</div>
      </div>
    </aside>
  );
}

function TopBar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur md:px-6">
      <button
        onClick={onMenu}
        className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden"
        aria-label="Toggle navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="hidden items-center gap-2 md:flex">
        <Car className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-foreground">{vehicleInfo.name}</span>
        <span className="text-xs text-muted-foreground">· {vehicleInfo.session}</span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <StatusPill icon={<Database className="h-3.5 w-3.5" />} label="Dataset" value={vehicleInfo.datasetStatus} tone="success" />
        <StatusPill icon={<Activity className="h-3.5 w-3.5" />} label="Analysis" value={vehicleInfo.analysisStatus} tone="primary" />
        <div className="ml-2 flex h-9 w-9 items-center justify-center rounded-full bg-elevated text-xs font-semibold text-foreground ring-1 ring-border">
          AK
        </div>
      </div>
    </header>
  );
}

function StatusPill({
  icon, label, value, tone,
}: { icon: ReactNode; label: string; value: string; tone: "success" | "primary" | "warning" }) {
  const toneClass = {
    success: "text-success ring-success/30 bg-success/10",
    primary: "text-primary ring-primary/30 bg-primary/10",
    warning: "text-warning ring-warning/30 bg-warning/10",
  }[tone];
  return (
    <div className={`hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 sm:flex ${toneClass}`}>
      {icon}
      <span className="text-muted-foreground/90">{label}</span>
      <span>{value}</span>
    </div>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="relative h-full w-64">
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute -right-10 top-3 rounded-md bg-card p-2 text-foreground"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMobileOpen(true)} />
        <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
