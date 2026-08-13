import { NextResponse } from 'next/server';
import { clearSessionCookies } from '@/services/session';

export async function POST() {
  clearSessionCookies();
  return NextResponse.json({ ok: true });
}
