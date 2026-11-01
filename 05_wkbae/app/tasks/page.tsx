'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { todayLocal } from '@/lib/dates';
import { periodRange, PERIODS, type Period } from '@/lib/period';
import { calcProgress } from '@/lib/progress';
import type { Task } from '@/lib/types';
import { ProgressBar } from '@/components/ProgressBar';

const STATUS_LABELS = { todo: '할 일', doing: '진행 중', done: '완료' };

export default function TasksPage() {
  const [period, setPeriod] = useState<Period>('day');
  const [date, setDate] = useState(todayLocal);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [error, setError] = useState('');

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
  }, [period, date]);

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
            <span className="text-slate-500">
              {task.date} · 가중치 {task.weight} · {STATUS_LABELS[task.status]}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
