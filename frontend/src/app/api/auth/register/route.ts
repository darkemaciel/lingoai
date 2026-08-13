import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '@/services/api-client';
import { toErrorResponse } from '@/services/bff';
import type { RegisterRequest, RegisterResponse } from '@/services/types';

export async function POST(request: NextRequest) {
  const body = (await request.json()) as RegisterRequest;
  try {
    const result = await backendFetch<RegisterResponse>('/api/v1/auth/register', {
      method: 'POST',
      body,
    });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    return toErrorResponse(error);
  }
}
