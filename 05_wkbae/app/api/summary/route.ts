import { respond } from '@/lib/http';
import { getSummary } from '@/lib/repo/summary';
import { dateQuerySchema } from '@/lib/validation';

export function GET(request: Request) {
  const today = new URL(request.url).searchParams.get('today') ?? undefined;
  return respond(async () => getSummary(dateQuerySchema.parse(today)));
}
