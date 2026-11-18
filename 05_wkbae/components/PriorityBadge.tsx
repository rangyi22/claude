import { PRIORITY_LABELS, type TaskPriority } from '@/lib/types';

const STYLES: Record<TaskPriority, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-slate-200 text-slate-700',
};

export function PriorityBadge({ priority }: { priority: TaskPriority }) {
  return (
    <span
      className={`whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium ${STYLES[priority]}`}
    >
      {PRIORITY_LABELS[priority]}
    </span>
  );
}
