'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { clampDate } from '@/lib/dates';
import { calcProgress } from '@/lib/progress';
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  TASK_PRIORITIES,
  TASK_STATUSES,
  type Goal,
  type Month,
  type Task,
  type TaskStatus,
  type Week,
} from '@/lib/types';
import { Modal } from './Modal';

function text(data: FormData, name: string): string {
  return String(data.get(name) ?? '');
}

interface FormProps {
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

export function GoalForm({ goal, onClose, onSaved }: FormProps & { goal?: Goal }) {
  async function submit(data: FormData) {
    const body = { title: text(data, 'title'), year: Number(text(data, 'year')) };
    await (goal ? api(`/api/goals/${goal.id}`, 'PATCH', body) : api('/api/goals', 'POST', body));
    await onSaved();
  }

  return (
    <Modal
      title={goal ? 'Schedule 수정' : '새 Schedule'}
      submitLabel="저장"
      onClose={onClose}
      onSubmit={submit}
    >
      <label className="field">
        제목
        <input name="title" required defaultValue={goal?.title} className="input" autoFocus />
      </label>
      <label className="field">
        연도
        <input
          name="year"
          type="number"
          required
          defaultValue={goal?.year ?? new Date().getFullYear()}
          className="input"
        />
      </label>
    </Modal>
  );
}

type Plan = Pick<Week, 'id' | 'title' | 'startDate' | 'endDate'>;

interface PlanFormProps extends FormProps {
  goalId: string;
  plan?: Plan;
  label: string;
  endpoint: string;
}

// 주간 계획과 월간 계획은 입력 항목이 같아 한 폼을 함께 쓴다.
function PlanForm({ goalId, plan, label, endpoint, onClose, onSaved }: PlanFormProps) {
  async function submit(data: FormData) {
    const fields = {
      title: text(data, 'title'),
      startDate: text(data, 'startDate'),
      endDate: text(data, 'endDate'),
    };
    await (plan
      ? api(`${endpoint}/${plan.id}`, 'PATCH', fields)
      : api(endpoint, 'POST', { goalId, ...fields }));
    await onSaved();
  }

  return (
    <Modal
      title={plan ? `${label} 수정` : `새 ${label}`}
      submitLabel="저장"
      onClose={onClose}
      onSubmit={submit}
    >
      <label className="field">
        제목
        <input name="title" required defaultValue={plan?.title} className="input" autoFocus />
      </label>
      <label className="field">
        시작일
        <input
          name="startDate"
          type="date"
          required
          defaultValue={plan?.startDate}
          className="input"
        />
      </label>
      <label className="field">
        종료일
        <input name="endDate" type="date" required defaultValue={plan?.endDate} className="input" />
      </label>
    </Modal>
  );
}

interface WeekFormProps extends FormProps {
  goalId: string;
  week?: Week;
}

export function WeekForm({ goalId, week, onClose, onSaved }: WeekFormProps) {
  return (
    <PlanForm
      goalId={goalId}
      plan={week}
      label="주간 계획"
      endpoint="/api/weeks"
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

interface MonthFormProps extends FormProps {
  goalId: string;
  month?: Month;
}

export function MonthForm({ goalId, month, onClose, onSaved }: MonthFormProps) {
  return (
    <PlanForm
      goalId={goalId}
      plan={month}
      label="월간 계획"
      endpoint="/api/months"
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

interface TaskFormProps extends FormProps {
  weekId: string;
  defaultDate: string;
  weeks: Week[];
  task?: Task;
}

function contains(week: Week, date: string): boolean {
  return week.startDate <= date && date <= week.endDate;
}

export function TaskForm({ weekId, defaultDate, weeks, task, onClose, onSaved }: TaskFormProps) {
  const [linkedWeekId, setLinkedWeekId] = useState(task?.weekId ?? weekId);
  const [date, setDate] = useState(task?.date ?? defaultDate);
  const [weight, setWeight] = useState(task?.weight ?? 1);
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? 'todo');
  const [weekTasks, setWeekTasks] = useState<Task[] | null>(null);

  const linkedWeek = weeks.find((week) => week.id === linkedWeekId);

  // 선택한 주간 계획의 할 일을 불러와, 이 할 일이 진행률에 주는 영향을 미리 계산한다.
  useEffect(() => {
    if (!linkedWeekId) return;
    let stale = false;
    setWeekTasks(null);
    api<Task[]>(`/api/tasks?weekId=${linkedWeekId}`)
      .then((tasks) => {
        if (!stale) setWeekTasks(tasks);
      })
      .catch(() => {
        if (!stale) setWeekTasks(null);
      });
    return () => {
      stale = true;
    };
  }, [linkedWeekId]);

  // 마감일을 바꿨는데 선택한 주간 계획 기간 밖이면, 그 날짜가 속한 주간 계획으로 옮긴다.
  function changeDate(next: string) {
    setDate(next);
    if (!next || (linkedWeek && contains(linkedWeek, next))) return;
    const matches = weeks.filter((week) => contains(week, next));
    const match = matches.find((week) => week.goalId === linkedWeek?.goalId) ?? matches[0];
    if (match) setLinkedWeekId(match.id);
  }

  // 주간 계획을 바꿨는데 마감일이 그 기간 밖이면, 마감일을 기간 안으로 맞춘다.
  function changeWeek(nextId: string) {
    setLinkedWeekId(nextId);
    const next = weeks.find((week) => week.id === nextId);
    if (next && date && !contains(next, date))
      setDate(clampDate(date, next.startDate, next.endDate));
  }

  const others = (weekTasks ?? []).filter((candidate) => candidate.id !== task?.id);
  const before = weekTasks ? calcProgress(weekTasks) : null;
  const after = weekTasks ? calcProgress([...others, { weight, status }]) : null;

  async function submit(data: FormData) {
    const fields = {
      weekId: text(data, 'weekId'),
      title: text(data, 'title'),
      description: text(data, 'description'),
      priority: text(data, 'priority'),
      status: text(data, 'status'),
      date: text(data, 'date'),
      weight: Number(text(data, 'weight')),
    };
    await (task
      ? api(`/api/tasks/${task.id}`, 'PATCH', fields)
      : api('/api/tasks', 'POST', fields));
    await onSaved();
  }

  if (weeks.length === 0) {
    return (
      <Modal
        title={task ? '할 일 수정' : '새 할 일'}
        submitLabel="저장"
        submitDisabled
        onClose={onClose}
        onSubmit={submit}
      >
        <p className="text-sm">
          연결할 주간 계획이 없습니다.{' '}
          <Link href="/goals" className="text-indigo-700 hover:underline">
            Schedule에서 주간 계획을 먼저 만들어 주세요.
          </Link>
        </p>
      </Modal>
    );
  }

  return (
    <Modal
      title={task ? '할 일 수정' : '새 할 일'}
      submitLabel="저장"
      onClose={onClose}
      onSubmit={submit}
    >
      <label className="field">
        제목
        <input name="title" required defaultValue={task?.title} className="input" autoFocus />
      </label>
      <label className="field">
        설명
        <textarea
          name="description"
          rows={3}
          maxLength={2000}
          defaultValue={task?.description}
          className="input"
        />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="field">
          우선순위
          <select name="priority" defaultValue={task?.priority ?? 'medium'} className="input">
            {TASK_PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {PRIORITY_LABELS[priority]}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          상태
          <select
            name="status"
            value={status}
            onChange={(event) => setStatus(event.target.value as TaskStatus)}
            className="input"
          >
            {TASK_STATUSES.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="field">
          마감일
          <input
            name="date"
            type="date"
            required
            value={date}
            onChange={(event) => changeDate(event.target.value)}
            className="input"
          />
        </label>
        <label className="field">
          가중치
          <select
            name="weight"
            value={weight}
            onChange={(event) => setWeight(Number(event.target.value))}
            className="input"
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="field">
        주간 계획
        <select
          name="weekId"
          value={linkedWeekId}
          onChange={(event) => changeWeek(event.target.value)}
          className="input"
        >
          {weeks.map((week) => (
            <option key={week.id} value={week.id}>
              {week.title} ({week.startDate} ~ {week.endDate})
            </option>
          ))}
        </select>
      </label>
      {linkedWeek && date && !contains(linkedWeek, date) && (
        <p className="text-xs text-red-700">
          마감일이 선택한 주간 계획 기간({linkedWeek.startDate} ~ {linkedWeek.endDate}) 밖입니다.
        </p>
      )}
      {linkedWeek && before !== null && after !== null && (
        <p
          data-testid="week-impact"
          className="rounded-md bg-indigo-50 px-3 py-2 text-xs text-indigo-800"
        >
          {before === after
            ? `‘${linkedWeek.title}’ 진행률은 ${before}%로 그대로입니다.`
            : `‘${linkedWeek.title}’ 진행률이 ${before}% → ${after}%로 바뀝니다.`}
        </p>
      )}
    </Modal>
  );
}

interface DeleteDialogProps {
  label: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteDialog({ label, onClose, onConfirm }: DeleteDialogProps) {
  return (
    <Modal title="삭제 확인" submitLabel="삭제" danger onClose={onClose} onSubmit={onConfirm}>
      <p className="text-sm">{label}을(를) 삭제할까요?</p>
    </Modal>
  );
}
