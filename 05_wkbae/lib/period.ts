import { addDays, mondayOf } from './dates';

export const PERIODS = [
  { value: 'day', label: '일일' },
  { value: 'week', label: '주간' },
  { value: 'year', label: '연간' },
] as const;

export type Period = (typeof PERIODS)[number]['value'];

export function periodRange(period: Period, date: string): { from: string; to: string } {
  if (period === 'day') return { from: date, to: date };
  if (period === 'week') {
    const from = mondayOf(date);
    return { from, to: addDays(from, 6) };
  }
  const year = date.slice(0, 4);
  return { from: `${year}-01-01`, to: `${year}-12-31` };
}
