/**
 * @file hooks/useTelemetry.ts
 * @description React Query hook for `GET /api/sessions/{session_id}/telemetry`.
 *
 * Backend returns 5 sensors: rpm, speed, maf, map, throttle.
 * coolant / intake / pedal are not available from the backend schema.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getTelemetry } from "@/api/services";
import { ApiClientError } from "@/api/client";
import type { TelemetryResponse } from "@/api/types";
import { useSessionStore } from "@/lib/sessionStore";

export const telemetryQueryKey = (sessionId: string) =>
  ["telemetry", sessionId] as const;

/**
 * Fetch and cache telemetry time-series data for the active session.
 *
 * @returns Standard TanStack Query result with `data: TelemetryResponse | undefined`.
 */
export function useTelemetry(): UseQueryResult<TelemetryResponse, ApiClientError> {
  const { sessionId } = useSessionStore();

  return useQuery<TelemetryResponse, ApiClientError>({
    queryKey: telemetryQueryKey(sessionId ?? ""),
    queryFn: () => getTelemetry(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 30_000,
    retry: 1,
  });
}
