import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { ActivityAnswerResponse, SubmitActivityAnswerRequest } from '@/services/types';

export async function POST(request: NextRequest, { params }: { params: { id: string } }) {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  const body = (await request.json()) as SubmitActivityAnswerRequest;
  try {
    const result = await backendFetch<ActivityAnswerResponse>(
      `/api/v1/activities/${params.id}/answers`,
      { method: 'POST', body, accessToken: token },
    );
    return NextResponse.json(result);
  } catch (error) {
    return toErrorResponse(error);
  }
}
