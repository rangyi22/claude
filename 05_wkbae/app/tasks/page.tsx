'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { todayLocal } from '@/lib/dates';
import { periodRange, PERIODS, type Period } from '@/lib/period';
import { calcProgress } from '@/lib/progress';
import type { Task, Week } from '@/lib/types';
import { DeleteDialog, TaskForm } from '@/components/forms';
import { ProgressBar } from '@/components/ProgressBar';

const STATUS_LABELS = { todo: '할 일', doing: '진행 중', done: '완료' };

type Dialog = { kind: 'form'; task: Task } | { kind: 'delete'; task: Task } | null;

export default function TasksPage() {
  const [period, setPeriod] = useState<Period>('day');
  const [date, setDate] = useState(todayLocal);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Week[]>('/api/weeks')
      .then(setWeeks)
      .catch((caught: Error) => setError(caught.message));
  }, [reloadKey]);

  function saved() {
    setDialog(null);
    setReloadKey((key) => key + 1);
  }

  useEffect(() => {
    let stale = false;
    const { from, to } = periodRange(period, date);
    api<Task[]>(`/api/tasks?from=${from}&to=${to}`)
      .then((result) => {
        if (stale) return;
        setError('');
        setTasks(result);
      })
      .catch((caught: Error) => {
        if (!stale) setError(caught.message);
      });
    return () => {
      stale = true;
    };
  }, [period, date, reloadKey]);

  const { from, to } = periodRange(period, date);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">기간별 보기</h1>
      <div className="flex flex-wrap items-center gap-2">
        {PERIODS.map(({ value, label }) => (
          <button
            key={value}
            className={period === value ? 'btn-primary' : 'btn'}
            aria-pressed={period === value}
            onClick={() => setPeriod(value)}
          >
            {label}
          </button>
        ))}
        <input
          type="date"
          aria-label="기준 날짜"
          required
          value={date}
          onChange={(event) => event.target.value && setDate(event.target.value)}
          className="input"
        />
        <span className="text-sm text-slate-500">
          {from} ~ {to}
        </span>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {tasks && (
        <div className="card">
          <ProgressBar value={calcProgress(tasks)} label="기간 진행률" />
        </div>
      )}
      {tasks?.length === 0 && <p className="text-sm text-slate-600">이 기간의 할 일이 없습니다.</p>}
      <ul className="flex flex-col gap-2">
        {tasks?.map((task) => (
          <li
            key={task.id}
            data-testid="period-task"
            className="card flex items-center justify-between gap-4 text-sm"
          >
            <Link href={`/weeks/${task.weekId}`} className="font-medium hover:underline">
              {task.title}
            </Link>
            <span className="flex items-center gap-3">
              <span className="text-slate-500">
                {task.date} · 가중치 {task.weight} · {STATUS_LABELS[task.status]}
              </span>
              <button className="btn" onClick={() => setDialog({ kind: 'form', task })}>
                수정
              </button>
              <button className="btn-danger" onClick={() => setDialog({ kind: 'delete', task })}>
                삭제
              </button>
            </span>
          </li>
        ))}
      </ul>
      {dialog?.kind === 'form' && (
        <TaskForm
          weekId={dialog.task.weekId}
          defaultDate={dialog.task.date}
          weeks={weeks}
          task={dialog.task}
          onClose={() => setDialog(null)}
          onSaved={saved}
        />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog
          label={dialog.task.title}
          onClose={() => setDialog(null)}
          onConfirm={async () => {
            await api(`/api/tasks/${dialog.task.id}`, 'DELETE');
            saved();
          }}
        />
      )}
    </div>
  );
}
