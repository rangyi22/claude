import type { TaskStatus } from './types';

interface ProgressTask {
  weight: number;
  status: TaskStatus;
}

export function calcProgress(tasks: readonly ProgressTask[]): number {
  const total = tasks.reduce((sum, task) => sum + task.weight, 0);
  if (total === 0) return 0;
  const done = tasks
    .filter((task) => task.status === 'done')
    .reduce((sum, task) => sum + task.weight, 0);
  return Math.round((done / total) * 100);
}
