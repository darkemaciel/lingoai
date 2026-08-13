import { NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { toErrorResponse } from '@/services/bff';
import { getRefreshToken, setAccessTokenCookie } from '@/services/session';
import type { AccessTokenResponse } from '@/services/types';

export async function POST() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return NextResponse.json(
      { error: { code: 'unauthorized', message: 'No refresh token' } },
      { status: 401 },
    );
  }
  try {
    const result = await backendFetch<AccessTokenResponse>('/api/v1/auth/refresh', {
      method: 'POST',
      body: { refresh_token: refreshToken },
    });
    setAccessTokenCookie(result.access_token);
    return NextResponse.json({ ok: true });
  } catch (error) {
    return toErrorResponse(error);
  }
}
