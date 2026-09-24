import axios, { AxiosError, type AxiosInstance } from 'axios';
import type { Conflict, Violation } from '@/types/api';

const TOKEN_KEY = 'ttg_access_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

let onUnauthorized: (() => void) | null = null;

/** App shell registers this so any 401 forces logout + login redirect. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 120000, // generation can take tens of seconds
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      clearToken();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

export default api;

/** Structured conflict payload returned by edit/publish endpoints (409). */
export interface ConflictPayload {
  error: string;
  conflicts: Conflict[];
  suggestions: string[];
}

/** Normalize any API error into something UI-friendly. */
export interface ApiErrorInfo {
  status: number | null;
  message: string;
  conflicts: Conflict[];
  violations: Violation[];
  suggestions: string[];
  /** Machine code for conflict bodies, e.g. TIMETABLE_CONFLICT, STALE_TIMETABLE. */
  code: string | null;
}

function extractConflicts(detail: unknown): Conflict[] {
  if (typeof detail === 'object' && detail !== null && 'conflicts' in detail) {
    const list = (detail as { conflicts?: unknown }).conflicts;
    if (Array.isArray(list)) return list as Conflict[];
  }
  return [];
}

function extractViolations(detail: unknown): Violation[] {
  if (typeof detail === 'object' && detail !== null) {
    const d = detail as Record<string, unknown>;
    for (const key of ['violations', 'errors']) {
      if (Array.isArray(d[key])) return d[key] as Violation[];
    }
  }
  return [];
}

export function parseApiError(error: unknown): ApiErrorInfo {
  const fallback: ApiErrorInfo = {
    status: null,
    message: error instanceof Error ? error.message : 'Unexpected error',
    conflicts: [],
    violations: [],
    suggestions: [],
    code: null,
  };
  // Duck-type the axios response shape so plain test doubles work too.
  const response =
    typeof error === 'object' && error !== null && 'response' in error
      ? (error as { response?: { status?: number; data?: unknown } }).response
      : undefined;
  if (!response) return fallback;
  const statusCode = response.status ?? null;
  const detail = (response.data as { detail?: unknown } | undefined)?.detail;
  const conflicts = extractConflicts(detail);
  const violations = extractViolations(detail);
  const suggestions =
    typeof detail === 'object' && detail !== null && Array.isArray((detail as { suggestions?: unknown }).suggestions)
      ? ((detail as { suggestions: string[] }).suggestions)
      : conflicts.flatMap((c) => c.suggestions ?? []);
  const code =
    typeof detail === 'object' && detail !== null && typeof (detail as { error?: unknown }).error === 'string'
      ? ((detail as { error: string }).error)
      : null;

  let message = 'Something went wrong. Please try again.';
  if (typeof detail === 'string' && detail.trim()) {
    message = detail;
  } else if (code === 'STALE_TIMETABLE') {
    message = 'This timetable was changed by another action. Refresh before making further changes.';
  } else if (conflicts.length > 0) {
    message = conflicts[0].message;
  } else if (violations.length > 0) {
    message = violations[0].message;
  } else if (Array.isArray(detail)) {
    // Pydantic 422 shape: [{loc, msg, ...}]
    const first = detail[0] as { msg?: string; loc?: (string | number)[] } | undefined;
    const where = first?.loc?.slice(1).join('.');
    message = `${where ? `${where}: ` : ''}${first?.msg ?? 'Invalid input'}`;
  } else if (statusCode === 401) {
    message = 'Your session expired. Please log in again.';
  } else if (statusCode === 403) {
    message = 'You do not have permission to perform this action.';
  } else if (statusCode === 404) {
    message = 'The requested resource was not found.';
  } else if (statusCode && statusCode >= 500) {
    message = 'Server error. Please try again later.';
  }
  return { status: statusCode, message, conflicts, violations, suggestions, code };
}

/** Human label for a period, e.g. "Monday · 09:00–10:00 · P1". */
export function periodLabel(p: {
  day_of_week: string;
  start_time: string;
  end_time: string;
  period_order: number;
}): string {
  const day = p.day_of_week.charAt(0) + p.day_of_week.slice(1).toLowerCase();
  const trim = (t: string) => t.slice(0, 5);
  return `${day} · ${trim(p.start_time)}–${trim(p.end_time)} · P${p.period_order}`;
}
