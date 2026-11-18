import { readJson, respond } from '@/lib/http';
import { deleteMonth, updateMonth } from '@/lib/repo/months';

interface Context {
  params: Promise<{ id: string }>;
}

export function PATCH(request: Request, { params }: Context) {
  return respond(async () => updateMonth((await params).id, await readJson(request)));
}

export function DELETE(_request: Request, { params }: Context) {
  return respond(async () => deleteMonth((await params).id));
}
