import { readJson, respond } from '@/lib/http';
import { carryOver } from '@/lib/repo/weeks';

interface Context {
  params: Promise<{ id: string }>;
}

export function POST(request: Request, { params }: Context) {
  return respond(async () => carryOver((await params).id, await readJson(request)));
}
