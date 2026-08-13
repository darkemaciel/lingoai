import { NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { PlacementResult } from '@/services/types';

export async function GET(_request: Request, { params }: { params: { id: string } }) {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  try {
    const result = await backendFetch<PlacementResult>(
      `/api/v1/placement/sessions/${params.id}/result`,
      { accessToken: token },
    );
    return NextResponse.json(result);
  } catch (error) {
    return toErrorResponse(error);
  }
}
