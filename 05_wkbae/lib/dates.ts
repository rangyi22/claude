const DAY_MS = 86_400_000;

function toTime(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

function fromTime(time: number): string {
  return new Date(time).toISOString().slice(0, 10);
}

export function isValidDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const time = toTime(value);
  return !Number.isNaN(time) && fromTime(time) === value;
}

export function addDays(date: string, days: number): string {
  return fromTime(toTime(date) + days * DAY_MS);
}

export function daysBetween(start: string, end: string): number {
  return Math.round((toTime(end) - toTime(start)) / DAY_MS);
}

export function mondayOf(date: string): string {
  const day = new Date(toTime(date)).getUTCDay();
  return addDays(date, -((day + 6) % 7));
}

export function clampDate(date: string, min: string, max: string): string {
  if (date < min) return min;
  return date > max ? max : date;
}

export function todayLocal(): string {
  const now = new Date();
  return fromTime(now.getTime() - now.getTimezoneOffset() * 60_000);
}
