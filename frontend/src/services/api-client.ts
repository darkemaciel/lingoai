// Server-only client for the LingoAI backend (FastAPI, /api/v1/*).
// Used exclusively by Next.js route handlers under src/app/api/** — the BFF layer.
// Browser code must never import this directly; it never sees the bearer token
// (research.md §10 — tokens live in an httpOnly cookie, not client-side JS).

import type { ApiError } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export class BackendApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'BackendApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  accessToken?: string;
}

export async function backendFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, accessToken } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  });

  if (!response.ok) {
    let parsed: ApiError | null = null;
    try {
      parsed = (await response.json()) as ApiError;
    } catch {
      // Non-JSON error body — fall through to the generic message below.
    }
    throw new BackendApiError(
      response.status,
      parsed?.error?.code ?? 'unknown_error',
      parsed?.error?.message ?? response.statusText,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
