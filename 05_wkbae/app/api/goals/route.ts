import { readJson, respond } from '@/lib/http';
import { createGoal, listGoals } from '@/lib/repo/goals';

export function GET() {
  return respond(listGoals);
}

export function POST(request: Request) {
  return respond(async () => createGoal(await readJson(request)), 201);
}
