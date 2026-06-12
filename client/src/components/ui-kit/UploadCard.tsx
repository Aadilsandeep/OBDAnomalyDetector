/**
 * @file components/ui-kit/UploadCard.tsx
 * @description CSV upload card component implementing the full upload workflow.
 *
 * Upload Flow:
 *   1. User selects / drops a CSV file
 *   2. `postAnalyze(file)` is called → `POST /api/analyze`
 *   3. On success: `sessionStore.setSession(sessionId)` is called
 *   4. Caller's `onSuccess` callback is invoked (typically navigates to `/`)
 *   5. On error: an inline error message is shown without crashing the UI
 *
 * Design:
 * - Drag-and-drop zone with visual feedback
 * - File validation (`.csv` only, size guard)
 * - Spinner + progress messaging during upload
 * - Fully accessible (keyboard-navigable input, ARIA labels)
 */

import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Upload, FileText, X, CheckCircle, Loader2 } from "lucide-react";
import { postAnalyze } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { AnalyzeResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface UploadCardProps {
  /** Called after a successful analysis. Typically used to navigate to `/`. */
  onSuccess?: (response: AnalyzeResponse) => void;
  /** Called when the user dismisses the card (if rendered in a dialog). */
  onDismiss?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Self-contained CSV upload card.
 * Manages its own drag state and wires directly to the session store.
 */
export function UploadCard({
  onSuccess,
  onDismiss,
}: UploadCardProps) {
  const { setSession } = useSessionStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // ------------------------------------------------------------------
  // React Query mutation
  // ------------------------------------------------------------------

  const mutation = useMutation<AnalyzeResponse, ApiClientError, File>({
    mutationFn: postAnalyze,
    onSuccess: (data) => {
      setSession(data.sessionId);
      setUploadSuccess(true);
      setTimeout(() => {
        onSuccess?.(data);
      }, 800); // brief success flash
    },
  });

  // ------------------------------------------------------------------
  // File validation
  // ------------------------------------------------------------------

  const validateFile = useCallback((file: File): string | null => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      return `"${file.name}" is not a CSV file. Please upload a .csv file.`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File exceeds ${MAX_FILE_SIZE_MB} MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB).`;
    }
    if (file.size === 0) {
      return "The selected file is empty.";
    }
    return null;
  }, []);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      const error = validateFile(file);
      if (error) {
        setValidationError(error);
        setSelectedFile(null);
        return;
      }
      setValidationError(null);
      setSelectedFile(file);
      mutation.reset();
      setUploadSuccess(false);
    },
    [validateFile, mutation],
  );

  // ------------------------------------------------------------------
  // Event handlers
  // ------------------------------------------------------------------

  const onInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => handleFiles(e.target.files),
    [handleFiles],
  );

  const onDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback(() => setIsDragging(false), []);

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const onSubmit = useCallback(() => {
    if (selectedFile) mutation.mutate(selectedFile);
  }, [selectedFile, mutation]);

  const onClearFile = useCallback(() => {
    setSelectedFile(null);
    setValidationError(null);
    mutation.reset();
    setUploadSuccess(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [mutation]);

  // ------------------------------------------------------------------
  // Derived state
  // ------------------------------------------------------------------

  const isRunning = mutation.isPending;
  const apiError = mutation.error?.message ?? null;
  const hasError = Boolean(validationError || apiError);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-foreground">
            Upload OBD-II Data
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            CSV · up to {MAX_FILE_SIZE_MB} MB
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            aria-label="Close upload dialog"
            className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Click or drag a CSV file here to upload"
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`relative flex min-h-36 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
          isDragging
            ? "border-primary bg-primary/5"
            : selectedFile
              ? "border-primary/40 bg-primary/4"
              : "border-border bg-elevated/30 hover:border-primary/40 hover:bg-primary/4"
        }`}
      >
        {uploadSuccess ? (
          <>
            <CheckCircle className="h-10 w-10 text-success" />
            <p className="text-sm font-medium text-success">
              Analysis complete!
            </p>
          </>
        ) : isRunning ? (
          <>
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">
              Running ML pipeline…
            </p>
          </>
        ) : selectedFile ? (
          <>
            <FileText className="h-10 w-10 text-primary" />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                {selectedFile.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(0)} KB · CSV
              </p>
            </div>
          </>
        ) : (
          <>
            <Upload className="h-10 w-10 text-muted-foreground/60" />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                Drop CSV here or click to browse
              </p>
              <p className="text-xs text-muted-foreground">
                OBD-II telemetry file (.csv)
              </p>
            </div>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        id="csv-file-upload"
        type="file"
        accept=".csv"
        className="sr-only"
        onChange={onInputChange}
        aria-label="CSV file input"
      />

      {/* Validation / API errors */}
      {hasError && !isRunning && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-critical/8 px-3 py-2.5 text-xs text-critical ring-1 ring-critical/20">
          <span className="mt-0.5 shrink-0">⚠</span>
          <span>{validationError ?? apiError}</span>
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2">
        {selectedFile && !isRunning && !uploadSuccess && (
          <button
            onClick={onClearFile}
            className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground"
          >
            Clear
          </button>
        )}
        <button
          id="upload-analyze-btn"
          onClick={onSubmit}
          disabled={!selectedFile || isRunning || uploadSuccess}
          className="ml-auto inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Analyze
            </>
          )}
        </button>
      </div>
    </div>
  );
}
