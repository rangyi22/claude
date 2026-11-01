import { addDays, mondayOf } from './dates';

interface MetricWeek {
  startDate: string;
  progress: number;
  taskCount: number;
}

export interface Metrics {
  planStreak: number;
  completionRate: number;
}

export function calcMetrics(weeks: readonly MetricWeek[], today: string): Metrics {
  const active = weeks.filter((week) => week.taskCount > 0 && week.startDate <= today);
  const mondays = new Set(active.map((week) => mondayOf(week.startDate)));

  // 이번 주 계획을 아직 안 세웠어도 지난주까지의 연속 기록은 끊지 않는다.
  let cursor = mondayOf(today);
  if (!mondays.has(cursor)) cursor = addDays(cursor, -7);
  let planStreak = 0;
  while (mondays.has(cursor)) {
    planStreak += 1;
    cursor = addDays(cursor, -7);
  }

  // 계획 개수가 아니라 달력 기준 최근 4주다. 계획이 없는 주는 평균에서 뺀다.
  const windowStart = addDays(mondayOf(today), -21);
  const recent = active.filter((week) => mondayOf(week.startDate) >= windowStart);
  const completionRate =
    recent.length === 0
      ? 0
      : Math.round(recent.reduce((sum, week) => sum + week.progress, 0) / recent.length);

  return { planStreak, completionRate };
}
