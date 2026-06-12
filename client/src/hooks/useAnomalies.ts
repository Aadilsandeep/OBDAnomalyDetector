/**
 * @file hooks/useAnomalies.ts
 * @description React Query hook for `GET /api/sessions/{session_id}/anomalies`.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getAnomalies } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { AnomaliesResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

export const anomaliesQueryKey = (sessionId: string) =>
  ["anomalies", sessionId] as const;

/**
 * Fetch and cache anomaly data for the active session.
 *
 * @returns Standard TanStack Query result with `data: AnomaliesResponse | undefined`.
 */
export function useAnomalies(): UseQueryResult<AnomaliesResponse, ApiClientError> {
  const { sessionId } = useSessionStore();

  return useQuery<AnomaliesResponse, ApiClientError>({
    queryKey: anomaliesQueryKey(sessionId ?? ""),
    queryFn: () => getAnomalies(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 30_000,
    retry: 1,
  });
}
