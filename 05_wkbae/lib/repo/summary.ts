import { todayLocal } from '../dates';
import { calcMetrics, type Metrics } from '../metrics';
import type { Goal, Week } from '../types';
import { listGoals } from './goals';
import { listWeeks } from './weeks';

export interface Summary {
  metrics: Metrics;
  goals: (Goal & { weeks: Week[] })[];
}

export async function getSummary(today = todayLocal()): Promise<Summary> {
  const [goals, weeks] = await Promise.all([listGoals(), listWeeks()]);
  return {
    metrics: calcMetrics(weeks, today),
    goals: goals.map((goal) => ({
      ...goal,
      weeks: weeks.filter((week) => week.goalId === goal.id),
    })),
  };
}
