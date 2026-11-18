'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { DeleteDialog, GoalForm, WeekForm } from '@/components/forms';
import { MonthSection } from '@/components/MonthSection';
import { ProgressBar } from '@/components/ProgressBar';
import { api } from '@/lib/api';
import type { Goal, Month, Week } from '@/lib/types';

type Dialog =
  | { kind: 'goal'; goal?: Goal }
  | { kind: 'deleteGoal'; goal: Goal }
  | { kind: 'week'; goalId: string; week?: Week }
  | { kind: 'deleteWeek'; week: Week }
  | null;

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[] | null>(null);
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [months, setMonths] = useState<Month[]>([]);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [goalList, weekList, monthList] = await Promise.all([
        api<Goal[]>('/api/goals'),
        api<Week[]>('/api/weeks'),
        api<Month[]>('/api/months'),
      ]);
      setGoals(goalList);
      setWeeks(weekList);
      setMonths(monthList);
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
        <h1 className="text-2xl font-bold">Schedule</h1>
        <button className="btn-primary" onClick={() => setDialog({ kind: 'goal' })}>
          새 Schedule
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {goals?.length === 0 && (
        <p className="text-sm text-slate-600">첫 Schedule을 만들어 보세요.</p>
      )}
      <ul className="flex flex-col gap-3">
        {goals?.map((goal) => {
          const goalWeeks = weeks.filter((week) => week.goalId === goal.id);
          const goalMonths = months.filter((month) => month.goalId === goal.id);
          return (
            <li key={goal.id} className="card flex flex-col gap-3" data-testid="goal-card">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-4">
                  <Link href={`/goals/${goal.id}`} className="font-semibold hover:underline">
                    {goal.title}
                  </Link>
                  <span className="flex items-center gap-3">
                    <span className="text-sm text-slate-500">
                      {goal.year}년 · 월간 계획 {goal.monthCount}개 · 주간 계획 {goal.weekCount}개
                    </span>
                    <button className="btn" onClick={() => setDialog({ kind: 'goal', goal })}>
                      수정
                    </button>
                    <button
                      className="btn-danger"
                      onClick={() => setDialog({ kind: 'deleteGoal', goal })}
                    >
                      삭제
                    </button>
                  </span>
                </div>
                <ProgressBar value={goal.progress} label={`${goal.title} 진행률`} />
              </div>

              <MonthSection
                goalId={goal.id}
                months={goalMonths}
                onChanged={load}
                className="border-t border-slate-200 pt-3"
              />

              <div className="flex flex-col gap-2 border-t border-slate-200 pt-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-slate-700">주간 계획</h2>
                  <button
                    className="btn"
                    onClick={() => setDialog({ kind: 'week', goalId: goal.id })}
                  >
                    주간 계획 추가
                  </button>
                </div>
                {goalWeeks.length === 0 && (
                  <p className="text-sm text-slate-600">주간 계획이 없습니다.</p>
                )}
                <ul className="flex flex-col gap-2">
                  {goalWeeks.map((week) => (
                    <li
                      key={week.id}
                      data-testid="goal-week"
                      className="flex flex-col gap-1 rounded-md bg-slate-50 p-3"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <Link
                          href={`/weeks/${week.id}`}
                          className="text-sm font-medium hover:underline"
                        >
                          {week.title}
                        </Link>
                        <span className="flex items-center gap-3">
                          <span className="text-xs text-slate-500">
                            {week.startDate} ~ {week.endDate} ·{' '}
                            <span className="whitespace-nowrap">할 일 {week.taskCount}개</span>
                          </span>
                          <button
                            className="btn"
                            aria-label={`${week.title} 수정`}
                            onClick={() => setDialog({ kind: 'week', goalId: goal.id, week })}
                          >
                            수정
                          </button>
                          <button
                            className="btn-danger"
                            aria-label={`${week.title} 삭제`}
                            onClick={() => setDialog({ kind: 'deleteWeek', week })}
                          >
                            삭제
                          </button>
                        </span>
                      </div>
                      <ProgressBar value={week.progress} label={`${week.title} 진행률`} />
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          );
        })}
      </ul>
      {dialog?.kind === 'goal' && (
        <GoalForm goal={dialog.goal} onClose={() => setDialog(null)} onSaved={saved} />
      )}
      {dialog?.kind === 'deleteGoal' && (
        <DeleteDialog
          label={dialog.goal.title}
          onClose={() => setDialog(null)}
          onConfirm={async () => {
            await api(`/api/goals/${dialog.goal.id}`, 'DELETE');
            await saved();
          }}
        />
      )}
      {dialog?.kind === 'week' && (
        <WeekForm
          goalId={dialog.goalId}
          week={dialog.week}
          onClose={() => setDialog(null)}
          onSaved={saved}
        />
      )}
      {dialog?.kind === 'deleteWeek' && (
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
