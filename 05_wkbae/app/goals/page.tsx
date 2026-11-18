'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { DeleteDialog, GoalForm } from '@/components/forms';
import { ProgressBar } from '@/components/ProgressBar';
import { api } from '@/lib/api';
import type { Goal } from '@/lib/types';

type Dialog = { kind: 'form'; goal?: Goal } | { kind: 'delete'; goal: Goal } | null;

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[] | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setGoals(await api<Goal[]>('/api/goals'));
    } catch (caught) {
      setError((caught as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function saved() {
    setDialog(null);
    await load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">1년 목표</h1>
        <button className="btn-primary" onClick={() => setDialog({ kind: 'form' })}>
          새 목표
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {goals?.length === 0 && <p className="text-sm text-slate-600">첫 목표를 만들어 보세요.</p>}
      <ul className="flex flex-col gap-3">
        {goals?.map((goal) => (
          <li key={goal.id} className="card flex flex-col gap-2" data-testid="goal-card">
            <div className="flex items-center justify-between gap-4">
              <Link href={`/goals/${goal.id}`} className="font-semibold hover:underline">
                {goal.title}
              </Link>
              <span className="text-sm text-slate-500">
                {goal.year}년 · 주간 계획 {goal.weekCount}개
              </span>
            </div>
            <ProgressBar value={goal.progress} label={`${goal.title} 진행률`} />
            <div className="flex justify-end gap-2">
              <button className="btn" onClick={() => setDialog({ kind: 'form', goal })}>
                수정
              </button>
              <button className="btn-danger" onClick={() => setDialog({ kind: 'delete', goal })}>
                삭제
              </button>
            </div>
          </li>
        ))}
      </ul>
      {dialog?.kind === 'form' && (
        <GoalForm goal={dialog.goal} onClose={() => setDialog(null)} onSaved={saved} />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog
          label={dialog.goal.title}
          onClose={() => setDialog(null)}
          onConfirm={async () => {
            await api(`/api/goals/${dialog.goal.id}`, 'DELETE');
            await saved();
          }}
        />
      )}
    </div>
  );
}
