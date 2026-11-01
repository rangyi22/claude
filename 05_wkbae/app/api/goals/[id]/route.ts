import { readJson, respond } from '@/lib/http';
import { deleteGoal, getGoal, updateGoal } from '@/lib/repo/goals';

interface Context {
  params: Promise<{ id: string }>;
}

export function GET(_request: Request, { params }: Context) {
  return respond(async () => getGoal((await params).id));
}

export function PATCH(request: Request, { params }: Context) {
  return respond(async () => updateGoal((await params).id, await readJson(request)));
}

export function DELETE(_request: Request, { params }: Context) {
  return respond(async () => deleteGoal((await params).id));
}
