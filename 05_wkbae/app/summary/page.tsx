'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ProgressBar } from '@/components/ProgressBar';
import { api } from '@/lib/api';
import { todayLocal } from '@/lib/dates';
import type { Summary } from '@/lib/repo/summary';

export default function SummaryPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Summary>(`/api/summary?today=${todayLocal()}`)
      .then(setSummary)
      .catch((caught: Error) => setError(caught.message));
  }, []);

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    );
  }
  if (!summary) return <p className="text-sm text-slate-600">불러오는 중…</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">달성 현황</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card" data-testid="metric-streak">
          <p className="text-sm text-slate-600">주간 계획 유지 (목표 4주 연속)</p>
          <p className="text-3xl font-bold">{summary.metrics.planStreak}주</p>
        </div>
        <div className="card" data-testid="metric-completion">
          <p className="text-sm text-slate-600">최근 4주 할 일 완료율 (목표 60%)</p>
          <p className="text-3xl font-bold">{summary.metrics.completionRate}%</p>
        </div>
      </div>
      {summary.goals.map((goal) => (
        <section key={goal.id} className="card flex flex-col gap-3">
          <Link href={`/goals/${goal.id}`} className="font-semibold hover:underline">
            {goal.title} ({goal.year}년)
          </Link>
          <ProgressBar value={goal.progress} label={`${goal.title} 진행률`} />
          <ul className="flex flex-col gap-2 border-l-2 border-slate-200 pl-3">
            {goal.weeks.map((week) => (
              <li key={week.id} className="flex flex-col gap-1 text-sm">
                <Link href={`/weeks/${week.id}`} className="hover:underline">
                  {week.title} ({week.startDate} ~ {week.endDate})
                </Link>
                <ProgressBar value={week.progress} label={`${week.title} 진행률`} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
