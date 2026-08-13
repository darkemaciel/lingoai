import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { SubmitAnswerRequest, SubmitAnswerResponse } from '@/services/types';

export async function POST(request: NextRequest, { params }: { params: { id: string } }) {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  const body = (await request.json()) as SubmitAnswerRequest;
  try {
    const result = await backendFetch<SubmitAnswerResponse>(
      `/api/v1/placement/sessions/${params.id}/answers`,
      { method: 'POST', body, accessToken: token },
    );
    return NextResponse.json(result);
  } catch (error) {
    return toErrorResponse(error);
  }
}
