export const TASK_STATUSES = ['todo', 'doing', 'done'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export interface Goal {
  id: string;
  title: string;
  year: number;
  progress: number;
  weekCount: number;
}

export interface Week {
  id: string;
  goalId: string;
  title: string;
  startDate: string;
  endDate: string;
  progress: number;
  taskCount: number;
}

export interface Task {
  id: string;
  weekId: string;
  title: string;
  date: string;
  weight: number;
  status: TaskStatus;
  order: number;
}

export interface WeekDetail extends Week {
  goalTitle: string;
  goalProgress: number;
  tasks: Task[];
}

export interface GoalDetail extends Goal {
  weeks: Week[];
}

export interface ProgressSnapshot {
  weeks: Record<string, number>;
  goals: Record<string, number>;
}

export interface TaskMutationResult {
  task: Task;
  progress: ProgressSnapshot;
}
