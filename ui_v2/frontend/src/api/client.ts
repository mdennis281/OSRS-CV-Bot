/**
 * Shared fetch wrapper with error handling and automatic retry.
 *
 * GET requests are retried up to 5 times with exponential back-off
 * when the backend is unreachable (network error / 502 / 503).
 * Mutating requests (POST, PUT, DELETE, PATCH) are NOT retried.
 */

const BASE = '';  // Proxied via Vite in dev; same origin in prod

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 800;
const RETRYABLE_STATUSES = new Set([502, 503, 504]);

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function isRetryable(method: string): boolean {
  return method === 'GET' || method === 'HEAD';
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const retries = isRetryable(method) ? MAX_RETRIES : 0;

  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...init?.headers },
        ...init,
      });

      // Retry on transient server errors (backend still booting)
      if (RETRYABLE_STATUSES.has(res.status) && attempt < retries) {
        await sleep(BASE_DELAY_MS * 2 ** attempt);
        continue;
      }

      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(`API ${res.status}: ${text}`);
      }
      return res.json() as Promise<T>;
    } catch (err) {
      lastError = err;
      // Network-level failures (ECONNREFUSED, fetch failed, etc.) → retry
      if (err instanceof TypeError && attempt < retries) {
        await sleep(BASE_DELAY_MS * 2 ** attempt);
        continue;
      }
      // Non-retryable or retries exhausted
      if (!(err instanceof TypeError)) throw err;
    }
  }
  throw lastError;
}
