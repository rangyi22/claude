import { readJson, respond } from '@/lib/http';
import { createWeek, listWeeks } from '@/lib/repo/weeks';

export function GET(request: Request) {
  const goalId = new URL(request.url).searchParams.get('goalId') ?? undefined;
  return respond(() => listWeeks(goalId));
}

export function POST(request: Request) {
  return respond(async () => createWeek(await readJson(request)), 201);
}
