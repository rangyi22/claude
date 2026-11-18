import { readJson, respond } from '@/lib/http';
import { createMonth, listMonths } from '@/lib/repo/months';

export function GET(request: Request) {
  const goalId = new URL(request.url).searchParams.get('goalId') ?? undefined;
  return respond(() => listMonths(goalId));
}

export function POST(request: Request) {
  return respond(async () => createMonth(await readJson(request)), 201);
}
