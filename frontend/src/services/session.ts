// httpOnly cookie session storage for the BFF auth layer (research.md §10).
// Only used from Next.js route handlers / server components — never from client code.

import { cookies } from 'next/headers';

const ACCESS_TOKEN_COOKIE = 'lingoai_access_token';
const REFRESH_TOKEN_COOKIE = 'lingoai_refresh_token';

const isProduction = process.env.NODE_ENV === 'production';

export function setSessionCookies(accessToken: string, refreshToken: string): void {
  const store = cookies();
  store.set(ACCESS_TOKEN_COOKIE, accessToken, {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 15, // access token lifetime, research.md §10 (~15 min)
  });
  store.set(REFRESH_TOKEN_COOKIE, refreshToken, {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30, // refresh token lifetime (~30 days)
  });
}

export function setAccessTokenCookie(accessToken: string): void {
  cookies().set(ACCESS_TOKEN_COOKIE, accessToken, {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 15,
  });
}

export function clearSessionCookies(): void {
  const store = cookies();
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
}

export function getAccessToken(): string | undefined {
  return cookies().get(ACCESS_TOKEN_COOKIE)?.value;
}

export function getRefreshToken(): string | undefined {
  return cookies().get(REFRESH_TOKEN_COOKIE)?.value;
}
