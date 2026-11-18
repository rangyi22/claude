'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ProgressBar } from '@/components/ProgressBar';
import { api } from '@/lib/api';
import { todayLocal } from '@/lib/dates';
import { periodRange } from '@/lib/period';
import { calcProgress } from '@/lib/progress';
import { STATUS_LABELS, TASK_STATUSES, type Goal, type Task, type Week } from '@/lib/types';

interface Overview {
  today: string;
  goals: Goal[];
  weeks: Week[];
  tasks: Task[];
}

export default function HomePage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState('');

  // 오늘 날짜는 브라우저 시계로 구하므로, 서버 렌더링 결과와 어긋나지 않게 마운트 뒤에 계산한다.
  useEffect(() => {
    const today = todayLocal();
    const { from, to } = periodRange('week', today);
    Promise.all([
      api<Goal[]>('/api/goals'),
      api<Week[]>('/api/weeks'),
      api<Task[]>(`/api/tasks?from=${today}&to=${today}`),
    ])
      .then(([goals, allWeeks, tasks]) =>
        setOverview({
          today,
          goals,
          tasks,
          weeks: allWeeks.filter((week) => week.startDate <= to && week.endDate >= from),
        }),
      )
      .catch((caught: Error) => setError(caught.message));
  }, []);

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    );
  }
  if (!overview) return <p className="text-sm text-slate-600">불러오는 중…</p>;

  const { today, goals, weeks, tasks } = overview;
  const goalTitle = new Map(goals.map((goal) => [goal.id, goal.title]));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">할 일 관리</h1>
        <p className="text-sm text-slate-600">
          오늘 {today} · 오늘 할 일 {tasks.length}개
        </p>
      </div>

      {goals.length === 0 && (
        <div className="card flex items-center justify-between gap-4">
          <p className="text-sm">
            아직 목표가 없습니다. 1년 목표를 만들고 주간 계획과 할 일을 연결해 보세요.
          </p>
          <Link href="/goals" className="btn-primary whitespace-nowrap">
            목표 만들기
          </Link>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <section aria-label="오늘의 할 일" className="flex flex-col gap-3 md:col-span-2">
          <h2 className="text-lg font-bold">오늘의 할 일</h2>
          <div className="card flex flex-col gap-2">
            <ProgressBar value={calcProgress(tasks)} label="오늘 진행률" />
            <p className="text-sm text-slate-600">
              {TASK_STATUSES.map(
                (status) =>
                  `${STATUS_LABELS[status]} ${tasks.filter((task) => task.status === status).length}`,
              ).join(' · ')}
            </p>
          </div>
          {tasks.length === 0 && <p className="text-sm text-slate-600">오늘 할 일이 없습니다.</p>}
          <ul className="flex flex-col gap-2">
            {tasks.map((task) => (
              <li
                key={task.id}
                data-testid="today-task"
                className="card flex items-center justify-between gap-4 text-sm"
              >
                <Link href={`/weeks/${task.weekId}`} className="font-medium hover:underline">
                  {task.title}
                </Link>
                <span className="text-slate-500">
                  가중치 {task.weight} · {STATUS_LABELS[task.status]}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="이번 주 계획" className="flex flex-col gap-3">
          <h2 className="text-lg font-bold">이번 주 계획</h2>
          {weeks.length === 0 && (
            <p className="text-sm text-slate-600">
              이번 주 계획이 없습니다.{' '}
              <Link href="/goals" className="text-indigo-700 hover:underline">
                목표에서 주간 계획을 만들어 보세요.
              </Link>
            </p>
          )}
          <ul className="flex flex-col gap-3">
            {weeks.map((week) => (
              <li key={week.id} data-testid="home-week" className="card flex flex-col gap-2">
                <Link href={`/weeks/${week.id}`} className="font-semibold hover:underline">
                  {week.title}
                </Link>
                <div className="flex flex-col gap-0.5 text-xs text-slate-500">
                  <p>{goalTitle.get(week.goalId)}</p>
                  <p>
                    {week.startDate} ~ {week.endDate} ·{' '}
                    <span className="whitespace-nowrap">할 일 {week.taskCount}개</span>
                  </p>
                </div>
                <ProgressBar value={week.progress} label={`${week.title} 진행률`} />
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
