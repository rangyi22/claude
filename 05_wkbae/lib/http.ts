import { NextResponse } from 'next/server';
import { ZodError } from 'zod';
import { AppError } from './errors';

export async function readJson(request: Request): Promise<unknown> {
  try {
    return await request.json();
  } catch {
    throw new AppError(400, '요청 본문이 올바른 JSON이 아닙니다.');
  }
}

function toResponse(error: unknown): NextResponse {
  if (error instanceof AppError) {
    return NextResponse.json({ error: error.message, ...error.details }, { status: error.status });
  }
  if (error instanceof ZodError) {
    return NextResponse.json(
      { error: error.issues[0]?.message ?? '입력값이 올바르지 않습니다.' },
      { status: 400 },
    );
  }
  throw error;
}

export async function respond<T>(work: () => Promise<T>, status = 200): Promise<NextResponse> {
  try {
    return NextResponse.json((await work()) ?? null, { status });
  } catch (error) {
    return toResponse(error);
  }
}
