import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { SendMessageRequest, SendMessageResponse } from '@/services/types';

export async function POST(request: NextRequest, { params }: { params: { id: string } }) {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  const body = (await request.json()) as SendMessageRequest;
  try {
    const result = await backendFetch<SendMessageResponse>(
      `/api/v1/conversations/${params.id}/messages`,
      { method: 'POST', body, accessToken: token },
    );
    return NextResponse.json(result);
  } catch (error) {
    return toErrorResponse(error);
  }
}
