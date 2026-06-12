/**
 * @file hooks/useSensors.ts
 * @description React Query hook for `GET /api/sessions/{session_id}/sensors`.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getSensors } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { SensorsResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

export const sensorsQueryKey = (sessionId: string) =>
  ["sensors", sessionId] as const;

/**
 * Fetch and cache sensor correlation data for the active session.
 *
 * @returns Standard TanStack Query result with `data: SensorsResponse | undefined`.
 */
export function useSensors(): UseQueryResult<SensorsResponse, ApiClientError> {
  const { sessionId } = useSessionStore();

  return useQuery<SensorsResponse, ApiClientError>({
    queryKey: sensorsQueryKey(sessionId ?? ""),
    queryFn: () => getSensors(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 30_000,
    retry: 1,
  });
}
