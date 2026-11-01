import { readJson, respond } from '@/lib/http';
import { createTask, listTasks } from '@/lib/repo/tasks';
import { dateQuerySchema } from '@/lib/validation';

export function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  return respond(async () =>
    listTasks({
      weekId: params.get('weekId') ?? undefined,
      from: dateQuerySchema.parse(params.get('from') ?? undefined),
      to: dateQuerySchema.parse(params.get('to') ?? undefined),
    }),
  );
}

export function POST(request: Request) {
  return respond(async () => createTask(await readJson(request)), 201);
}
