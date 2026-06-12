/**
 * @file hooks/useReport.ts
 * @description React Query hook for `GET /api/sessions/{session_id}/report`.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getReport } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { ReportResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

export const reportQueryKey = (sessionId: string) =>
  ["report", sessionId] as const;

/**
 * Fetch and cache the executive report for the active session.
 *
 * @returns Standard TanStack Query result with `data: ReportResponse | undefined`.
 */
export function useReport(): UseQueryResult<ReportResponse, ApiClientError> {
  const { sessionId } = useSessionStore();

  return useQuery<ReportResponse, ApiClientError>({
    queryKey: reportQueryKey(sessionId ?? ""),
    queryFn: () => getReport(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 30_000,
    retry: 1,
  });
}
