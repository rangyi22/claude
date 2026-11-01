import { readJson, respond } from '@/lib/http';
import { deleteTask, updateTask } from '@/lib/repo/tasks';

interface Context {
  params: Promise<{ id: string }>;
}

export function PATCH(request: Request, { params }: Context) {
  return respond(async () => updateTask((await params).id, await readJson(request)));
}

export function DELETE(_request: Request, { params }: Context) {
  return respond(async () => deleteTask((await params).id));
}
