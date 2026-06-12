/**
 * @file hooks/useDashboard.ts
 * @description React Query hook for `GET /api/sessions/{session_id}/dashboard`.
 *
 * Returns a fully-typed `UseQueryResult` wrapping `DashboardResponse`.
 * Query is disabled when no `sessionId` is present in the session store.
 *
 * On 404 (session not found — backend restarted), the error is surfaced
 * via the query's `error` field and the session store is cleared so the
 * user is prompted to re-upload.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getDashboard } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { DashboardResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

/** Stable query key factory for dashboard queries. */
export const dashboardQueryKey = (sessionId: string) =>
  ["dashboard", sessionId] as const;

/**
 * Fetch and cache dashboard data for the active session.
 *
 * @returns Standard TanStack Query result with `data: DashboardResponse | undefined`.
 */
export function useDashboard(): UseQueryResult<DashboardResponse, ApiClientError> {
  const { sessionId, clearSession } = useSessionStore();

  return useQuery<DashboardResponse, ApiClientError>({
    queryKey: dashboardQueryKey(sessionId ?? ""),
    queryFn: async () => {
      try {
        return await getDashboard(sessionId!);
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 404) {
          // Session no longer exists on the server — clear stale localStorage entry
          clearSession();
        }
        throw err;
      }
    },
    enabled: Boolean(sessionId),
    staleTime: 30_000, // 30 s — dashboard data doesn't change after analysis
    retry: 1,
  });
}
