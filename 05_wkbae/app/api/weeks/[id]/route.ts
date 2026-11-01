import { readJson, respond } from '@/lib/http';
import { deleteWeek, getWeek, updateWeek } from '@/lib/repo/weeks';

interface Context {
  params: Promise<{ id: string }>;
}

export function GET(_request: Request, { params }: Context) {
  return respond(async () => getWeek((await params).id));
}

export function PATCH(request: Request, { params }: Context) {
  return respond(async () => updateWeek((await params).id, await readJson(request)));
}

export function DELETE(_request: Request, { params }: Context) {
  return respond(async () => deleteWeek((await params).id));
}
