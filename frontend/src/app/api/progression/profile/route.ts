import { NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { ProgressionProfileResponse } from '@/services/types';

export async function GET() {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  try {
    const result = await backendFetch<ProgressionProfileResponse>('/api/v1/progression/profile', {
      accessToken: token,
    });
    return NextResponse.json(result);
  } catch (error) {
    return toErrorResponse(error);
  }
}
