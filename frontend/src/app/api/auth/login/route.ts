import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { toErrorResponse } from '@/services/bff';
import { setSessionCookies } from '@/services/session';
import type { LoginRequest, TokenResponse } from '@/services/types';

export async function POST(request: NextRequest) {
  const body = (await request.json()) as LoginRequest;
  try {
    const tokens = await backendFetch<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body,
    });
    setSessionCookies(tokens.access_token, tokens.refresh_token);
    return NextResponse.json({ ok: true });
  } catch (error) {
    return toErrorResponse(error);
  }
}
