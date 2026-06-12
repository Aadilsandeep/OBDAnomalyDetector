/**
 * @file lib/sessionStore.tsx
 * @description Lightweight frontend session store implemented as React Context.
 *
 * Responsibilities:
 * - Hold the active `sessionId` (UUID from the backend `POST /api/analyze`).
 * - Persist `sessionId` to `localStorage` so page refreshes survive.
 * - Expose loading and error states used during the upload/analyse flow.
 * - Provide typed access via the `useSessionStore` hook.
 *
 * Design decisions:
 * - No Zustand / Redux — avoids adding new dependencies.
 * - No `createServerFn` — session state is purely client-side.
 * - `SessionStoreProvider` wraps the entire app via `AppLayout`.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LOCAL_STORAGE_KEY = "autoassist_session_id" as const;

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

export interface SessionStoreValue {
  /** Active session UUID, or `null` when no session has been uploaded. */
  sessionId: string | null;
  /** `true` while the upload / analysis request is in-flight. */
  isUploading: boolean;
  /** Human-readable error message, or `null` when no error is present. */
  uploadError: string | null;
  /** Store a new session after a successful upload. */
  setSession: (id: string) => void;
  /** Clear the current session (e.g. to upload a new file). */
  clearSession: () => void;
  /** Set the uploading flag from the upload mutation. */
  setUploading: (loading: boolean) => void;
  /** Set an error message from the upload mutation. */
  setUploadError: (error: string | null) => void;
}

const SessionStoreContext = createContext<SessionStoreValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/**
 * Provides session state to the entire component tree.
 *
 * Mount once at the application root (inside `AppLayout` or `__root.tsx`).
 */
export function SessionStoreProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [sessionId, setSessionIdState] = useState<string | null>(() => {
    // Hydrate from localStorage on first render
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEY) ?? null;
    } catch {
      return null;
    }
  });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadErrorState] = useState<string | null>(null);

  const setSession = useCallback((id: string): void => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, id);
    } catch {
      // localStorage unavailable in some environments (e.g. private browsing with restrictions)
    }
    setSessionIdState(id);
    setUploadErrorState(null);
  }, []);

  const clearSession = useCallback((): void => {
    try {
      localStorage.removeItem(LOCAL_STORAGE_KEY);
    } catch {
      // ignore
    }
    setSessionIdState(null);
  }, []);

  const setUploading = useCallback((loading: boolean): void => {
    setIsUploading(loading);
  }, []);

  const setUploadError = useCallback((error: string | null): void => {
    setUploadErrorState(error);
  }, []);

  const value = useMemo<SessionStoreValue>(
    () => ({
      sessionId,
      isUploading,
      uploadError,
      setSession,
      clearSession,
      setUploading,
      setUploadError,
    }),
    [
      sessionId,
      isUploading,
      uploadError,
      setSession,
      clearSession,
      setUploading,
      setUploadError,
    ],
  );

  return (
    <SessionStoreContext.Provider value={value}>
      {children}
    </SessionStoreContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Consume the session store from any component inside `SessionStoreProvider`.
 *
 * @throws {Error} If called outside of `SessionStoreProvider`.
 */
export function useSessionStore(): SessionStoreValue {
  const ctx = useContext(SessionStoreContext);
  if (ctx === null) {
    throw new Error(
      "useSessionStore must be used inside <SessionStoreProvider>",
    );
  }
  return ctx;
}
