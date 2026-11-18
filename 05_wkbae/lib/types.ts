export const TASK_STATUSES = ['todo', 'doing', 'done'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_PRIORITIES = ['high', 'medium', 'low'] as const;
export type TaskPriority = (typeof TASK_PRIORITIES)[number];

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
};

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: '할 일',
  doing: '진행 중',
  done: '완료',
};

export interface Goal {
  id: string;
  title: string;
  year: number;
  progress: number;
  weekCount: number;
  monthCount: number;
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

export interface Month {
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
  description: string;
  priority: TaskPriority;
}

export interface WeekDetail extends Week {
  goalTitle: string;
  goalProgress: number;
  tasks: Task[];
}

export interface GoalDetail extends Goal {
  weeks: Week[];
  months: Month[];
}

export interface ProgressSnapshot {
  weeks: Record<string, number>;
  goals: Record<string, number>;
}

export interface TaskMutationResult {
  task: Task;
  progress: ProgressSnapshot;
}
