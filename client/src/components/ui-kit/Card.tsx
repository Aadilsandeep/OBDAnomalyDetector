import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-card shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset,0_8px_24px_-12px_rgba(0,0,0,0.5)] ${className}`}
    >
      {children}
    </div>
  );
}

export function PanelHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

export function PanelBody({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`px-5 py-5 ${className}`}>{children}</div>;
}

export function StatusDot({ status }: { status: "healthy" | "monitor" | "warning" | "critical" }) {
  const map = {
    healthy: "bg-success shadow-[0_0_0_3px_color-mix(in_oklab,var(--success)_25%,transparent)]",
    monitor: "bg-warning shadow-[0_0_0_3px_color-mix(in_oklab,var(--warning)_25%,transparent)]",
    warning: "bg-warning shadow-[0_0_0_3px_color-mix(in_oklab,var(--warning)_25%,transparent)]",
    critical: "bg-critical shadow-[0_0_0_3px_color-mix(in_oklab,var(--critical)_25%,transparent)]",
  } as const;
  return <span className={`inline-block h-2 w-2 rounded-full ${map[status]}`} />;
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "critical" | "primary";
}) {
  const map = {
    neutral: "bg-muted text-muted-foreground ring-border",
    success: "bg-success/12 text-success ring-success/30",
    warning: "bg-warning/12 text-warning ring-warning/30",
    critical: "bg-critical/15 text-critical ring-critical/40",
    primary: "bg-primary/12 text-primary ring-primary/30",
  } as const;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${map[tone]}`}>
      {children}
    </span>
  );
}
