import { NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { requireAccessToken, toErrorResponse } from '@/services/bff';
import type { StartConversationResponse } from '@/services/types';

export async function POST() {
  const token = requireAccessToken();
  if (token instanceof NextResponse) return token;

  try {
    const result = await backendFetch<StartConversationResponse>('/api/v1/conversations', {
      method: 'POST',
      accessToken: token,
    });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    return toErrorResponse(error);
  }
}
