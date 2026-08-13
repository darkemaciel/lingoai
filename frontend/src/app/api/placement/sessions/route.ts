import { NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { StartPlacementSessionResponse } from '@/services/types';

export async function POST() {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  try {
    const result = await backendFetch<StartPlacementSessionResponse>('/api/v1/placement/sessions', {
      method: 'POST',
      accessToken: token,
    });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    return toErrorResponse(error);
  }
}
