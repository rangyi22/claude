'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useState } from 'react';
import { DeleteDialog, WeekForm } from '@/components/forms';
import { ProgressBar } from '@/components/ProgressBar';
import { api } from '@/lib/api';
import type { GoalDetail, Week } from '@/lib/types';

type Dialog = { kind: 'form'; week?: Week } | { kind: 'delete'; week: Week } | null;

export default function GoalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [goal, setGoal] = useState<GoalDetail | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setGoal(await api<GoalDetail>(`/api/goals/${id}`));
    } catch (caught) {
      setError((caught as Error).message);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saved() {
    setDialog(null);
    await load();
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    );
  }
  if (!goal) return <p className="text-sm text-slate-600">불러오는 중…</p>;

  return (
    <div className="flex flex-col gap-4">
      <Link href="/" className="text-sm text-indigo-700 hover:underline">
        ← 목표 목록
      </Link>
      <div className="card flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{goal.title}</h1>
          <span className="text-sm text-slate-500">{goal.year}년</span>
        </div>
        <ProgressBar value={goal.progress} label="목표 진행률" />
      </div>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">주간 계획</h2>
        <button className="btn-primary" onClick={() => setDialog({ kind: 'form' })}>
          새 주간 계획
        </button>
      </div>
      {goal.weeks.length === 0 && <p className="text-sm text-slate-600">주간 계획이 없습니다.</p>}
      <ul className="flex flex-col gap-3">
        {goal.weeks.map((week) => (
          <li key={week.id} className="card flex flex-col gap-2" data-testid="week-card">
            <div className="flex items-center justify-between gap-4">
              <Link href={`/weeks/${week.id}`} className="font-semibold hover:underline">
                {week.title}
              </Link>
              <span className="text-sm text-slate-500">
                {week.startDate} ~ {week.endDate} · 할 일 {week.taskCount}개
              </span>
            </div>
            <ProgressBar value={week.progress} label={`${week.title} 진행률`} />
            <div className="flex justify-end gap-2">
              <button className="btn" onClick={() => setDialog({ kind: 'form', week })}>
                수정
              </button>
              <button className="btn-danger" onClick={() => setDialog({ kind: 'delete', week })}>
                삭제
              </button>
            </div>
          </li>
        ))}
      </ul>
      {dialog?.kind === 'form' && (
        <WeekForm
          goalId={goal.id}
          week={dialog.week}
          onClose={() => setDialog(null)}
          onSaved={saved}
        />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog
          label={dialog.week.title}
          onClose={() => setDialog(null)}
          onConfirm={async () => {
            await api(`/api/weeks/${dialog.week.id}`, 'DELETE');
            await saved();
          }}
        />
      )}
    </div>
  );
}
