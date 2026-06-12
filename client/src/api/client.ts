/**
 * @file api/client.ts
 * @description Base HTTP client for the AutoAssist FastAPI backend.
 *
 * Responsibilities:
 * - Resolve the backend base URL from `VITE_API_BASE_URL` environment
 *   variable (defaults to `http://localhost:8000` for local development).
 * - Provide a typed `apiFetch` helper that handles JSON serialisation,
 *   non-2xx status codes, and network failures uniformly.
 * - Export a typed `ApiClientError` class for consumer error handling.
 *
 * Usage:
 * ```ts
 * const data = await apiFetch<DashboardResponse>("/api/sessions/abc/dashboard");
 * ```
 */

// ---------------------------------------------------------------------------
// Base URL
// ---------------------------------------------------------------------------

/**
 * Backend base URL resolved at build-time from Vite's `VITE_API_BASE_URL`
 * environment variable.  Trailing slashes are stripped for consistency.
 *
 * Set `VITE_API_BASE_URL=http://localhost:8000` in `.env.local` during
 * local development.  Leave unset to use the default.
 */
const API_BASE_URL: string = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000"
).replace(/\/$/, "");

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

/**
 * Typed error thrown by `apiFetch` when the backend returns a non-2xx
 * status or when the network request itself fails.
 */
export class ApiClientError extends Error {
  /** HTTP status code, or 0 for network-level failures. */
  public readonly status: number;

  public constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------

/**
 * Typed wrapper around the browser `fetch` API.
 *
 * @template T - Expected JSON response type.
 * @param path  - API path including leading slash (e.g. `/api/health`).
 * @param init  - Optional `RequestInit` overrides (method, headers, body…).
 * @returns Parsed JSON response cast to `T`.
 * @throws `ApiClientError` on non-2xx responses or network failures.
 */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers:
        init?.body instanceof FormData
          ? undefined // Let browser set multipart boundary automatically
          : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (networkError) {
    throw new ApiClientError(
      "Unable to reach the AutoAssist backend. Is the server running?",
      0,
    );
  }

  if (!response.ok) {
    // Attempt to extract FastAPI's structured error detail
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
      }
    } catch {
      // Non-JSON error body — fall back to the status text
      detail = response.statusText || detail;
    }
    throw new ApiClientError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

export { API_BASE_URL };
