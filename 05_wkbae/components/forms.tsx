'use client';

import { api } from '@/lib/api';
import type { Goal, Task, Week } from '@/lib/types';
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
      title={goal ? '목표 수정' : '새 목표'}
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

interface WeekFormProps extends FormProps {
  goalId: string;
  week?: Week;
}

export function WeekForm({ goalId, week, onClose, onSaved }: WeekFormProps) {
  async function submit(data: FormData) {
    const fields = {
      title: text(data, 'title'),
      startDate: text(data, 'startDate'),
      endDate: text(data, 'endDate'),
    };
    await (week
      ? api(`/api/weeks/${week.id}`, 'PATCH', fields)
      : api('/api/weeks', 'POST', { goalId, ...fields }));
    await onSaved();
  }

  return (
    <Modal
      title={week ? '주간 계획 수정' : '새 주간 계획'}
      submitLabel="저장"
      onClose={onClose}
      onSubmit={submit}
    >
      <label className="field">
        제목
        <input name="title" required defaultValue={week?.title} className="input" autoFocus />
      </label>
      <label className="field">
        시작일
        <input
          name="startDate"
          type="date"
          required
          defaultValue={week?.startDate}
          className="input"
        />
      </label>
      <label className="field">
        종료일
        <input name="endDate" type="date" required defaultValue={week?.endDate} className="input" />
      </label>
    </Modal>
  );
}

interface TaskFormProps extends FormProps {
  weekId: string;
  defaultDate: string;
  weeks: Week[];
  task?: Task;
}

export function TaskForm({ weekId, defaultDate, weeks, task, onClose, onSaved }: TaskFormProps) {
  async function submit(data: FormData) {
    const fields = {
      weekId: text(data, 'weekId'),
      title: text(data, 'title'),
      date: text(data, 'date'),
      weight: Number(text(data, 'weight')),
    };
    await (task
      ? api(`/api/tasks/${task.id}`, 'PATCH', fields)
      : api('/api/tasks', 'POST', fields));
    await onSaved();
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
        날짜
        <input
          name="date"
          type="date"
          required
          defaultValue={task?.date ?? defaultDate}
          className="input"
        />
      </label>
      <label className="field">
        가중치
        <select name="weight" defaultValue={task?.weight ?? 1} className="input">
          {[1, 2, 3, 4, 5].map((weight) => (
            <option key={weight} value={weight}>
              {weight}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        주간 계획
        <select name="weekId" defaultValue={task?.weekId ?? weekId} className="input">
          {weeks.map((week) => (
            <option key={week.id} value={week.id}>
              {week.title} ({week.startDate} ~ {week.endDate})
            </option>
          ))}
        </select>
      </label>
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
