'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import type { Month } from '@/lib/types';
import { DeleteDialog, MonthForm } from './forms';
import { ProgressBar } from './ProgressBar';

type Dialog = { kind: 'form'; month?: Month } | { kind: 'delete'; month: Month } | null;

interface MonthSectionProps {
  goalId: string;
  months: Month[];
  onChanged: () => void | Promise<void>;
  className?: string;
}

export function MonthSection({ goalId, months, onChanged, className }: MonthSectionProps) {
  const [dialog, setDialog] = useState<Dialog>(null);

  async function changed() {
    setDialog(null);
    await onChanged();
  }

  return (
    <div className={`flex flex-col gap-2 ${className ?? ''}`} data-testid="month-section">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-700">월간 계획</h2>
        <button className="btn" onClick={() => setDialog({ kind: 'form' })}>
          월간 계획 추가
        </button>
      </div>
      {months.length === 0 && <p className="text-sm text-slate-600">월간 계획이 없습니다.</p>}
      <ul className="flex flex-col gap-2">
        {months.map((month) => (
          <li
            key={month.id}
            data-testid="goal-month"
            className="flex flex-col gap-1 rounded-md bg-slate-50 p-3"
          >
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium">{month.title}</span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-slate-500">
                  {month.startDate} ~ {month.endDate} ·{' '}
                  <span className="whitespace-nowrap">할 일 {month.taskCount}개</span>
                </span>
                <button
                  className="btn"
                  aria-label={`${month.title} 수정`}
                  onClick={() => setDialog({ kind: 'form', month })}
                >
                  수정
                </button>
                <button
                  className="btn-danger"
                  aria-label={`${month.title} 삭제`}
                  onClick={() => setDialog({ kind: 'delete', month })}
                >
                  삭제
                </button>
              </span>
            </div>
            <ProgressBar value={month.progress} label={`${month.title} 진행률`} />
          </li>
        ))}
      </ul>
      {dialog?.kind === 'form' && (
        <MonthForm
          goalId={goalId}
          month={dialog.month}
          onClose={() => setDialog(null)}
          onSaved={changed}
        />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog
          label={dialog.month.title}
          onClose={() => setDialog(null)}
          onConfirm={async () => {
            await api(`/api/months/${dialog.month.id}`, 'DELETE');
            await changed();
          }}
        />
      )}
    </div>
  );
}
