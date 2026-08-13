// Shared helpers for BFF route handlers (src/app/api/**) — translating
// BackendApiError into the same {"error":{"code","message"}} shape the
// backend itself uses (contracts/rest-api.md "Cross-cutting"), and
// resolving the caller's access token from the httpOnly session cookie.

import { NextResponse } from 'next/server';
import { BackendApiError } from './api-client';
import { getAccessToken } from './session';

export function requireAccessToken(): string | NextResponse {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'unauthorized', message: 'Not authenticated' } },
      { status: 401 },
    );
  }
  return token;
}

export function toErrorResponse(error: unknown): NextResponse {
  if (error instanceof BackendApiError) {
    return NextResponse.json(
      { error: { code: error.code, message: error.message } },
      { status: error.status },
    );
  }
  return NextResponse.json(
    { error: { code: 'internal_error', message: 'Unexpected server error' } },
    { status: 500 },
  );
}
