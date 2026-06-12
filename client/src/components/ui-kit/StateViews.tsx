/**
 * @file components/ui-kit/StateViews.tsx
 * @description Reusable UI components for loading, error, and empty states.
 *
 * Used across all pages that depend on live API data. Ensures a consistent
 * feedback pattern when data is loading, unavailable, or errored.
 */

import { AlertTriangle, Loader2, Upload } from "lucide-react";
import type { ReactElement, ReactNode } from "react";

// ---------------------------------------------------------------------------
// LoadingState
// ---------------------------------------------------------------------------

/**
 * Full-height centred spinner with an optional label.
 * Use inside any page panel while a query is in `isLoading` state.
 */
export function LoadingState({
  label = "Loading data…",
}: {
  label?: string;
}): ReactElement {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-muted-foreground">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ErrorState
// ---------------------------------------------------------------------------

/**
 * Error card with message and optional retry action.
 *
 * @param message - Human-readable error message from `ApiClientError`.
 * @param onRetry - Optional callback to re-trigger the failed query.
 */
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}): ReactElement {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center gap-4 rounded-lg border border-border bg-elevated/30 px-6 py-8 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-critical/10 text-critical ring-1 ring-critical/30">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">
          Failed to load data
        </p>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md bg-primary/10 px-4 py-2 text-sm font-medium text-primary ring-1 ring-primary/25 transition-opacity hover:opacity-80"
        >
          Try again
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

/**
 * Full-page empty state shown when no session has been uploaded.
 * Prompts the user to upload a CSV via the sidebar upload button.
 *
 * @param onUpload - Optional callback to programmatically open the upload dialog.
 */
export function EmptyState({
  onUpload,
}: {
  onUpload?: () => void;
}): ReactElement {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 text-center">
      <div className="grid h-20 w-20 place-items-center rounded-2xl bg-primary/8 text-primary ring-1 ring-primary/20">
        <Upload className="h-10 w-10" />
      </div>
      <div className="max-w-sm">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          No session loaded
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Upload an OBD-II CSV file to run the analysis pipeline and explore
          vehicle health, anomalies, and telemetry data.
        </p>
      </div>
      {onUpload && (
        <button
          onClick={onUpload}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Upload className="h-4 w-4" />
          Upload CSV file
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// InlineError
// ---------------------------------------------------------------------------

/**
 * Small inline error banner for use inside panels.
 */
export function InlineError({ children }: { children: ReactNode }): ReactElement {
  return (
    <div className="flex items-center gap-2 rounded-md bg-critical/8 px-3 py-2 text-xs text-critical ring-1 ring-critical/20">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}
