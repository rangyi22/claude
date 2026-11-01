'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useRef, useState } from 'react';
import { Board } from '@/components/Board';
import { DeleteDialog, TaskForm } from '@/components/forms';
import { Modal } from '@/components/Modal';
import { ProgressBar } from '@/components/ProgressBar';
import { api, ApiError } from '@/lib/api';
import { createMoveQueue, type MoveQueue } from '@/lib/moveQueue';
import { calcProgress } from '@/lib/progress';
import type { Task, TaskMutationResult, TaskStatus, Week, WeekDetail } from '@/lib/types';
import type { CarryOverResult } from '@/lib/repo/weeks';

type Dialog =
  | { kind: 'form'; task?: Task }
  | { kind: 'delete'; task: Task }
  | { kind: 'createNextWeek' }
  | null;

export default function WeekPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [week, setWeek] = useState<WeekDetail | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [goalProgress, setGoalProgress] = useState(0);
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const latestLoad = useRef(0);
  const queue = useRef<MoveQueue | null>(null);
  const goalId = useRef('');
  const ordersBeforeMove = useRef(new Map<string, number>());

  const load = useCallback(async () => {
    const loadId = ++latestLoad.current;
    try {
      const [detail, allWeeks] = await Promise.all([
        api<WeekDetail>(`/api/weeks/${id}`),
        api<Week[]>('/api/weeks'),
      ]);
      // 이동 중에 받은 응답은 낙관적 화면을 되돌릴 수 있어 버린다. 이동이 끝나면 다시 불러온다.
      if (loadId !== latestLoad.current || queue.current?.isBusy()) return;
      goalId.current = detail.goalId;
      setWeek(detail);
      setTasks(detail.tasks);
      setGoalProgress(detail.goalProgress);
      setWeeks(allWeeks);
    } catch (caught) {
      setError((current) => current || (caught as Error).message);
    }
  }, [id]);

  useEffect(() => {
    queue.current = createMoveQueue<TaskMutationResult>({
      send: (taskId, status) => api(`/api/tasks/${taskId}`, 'PATCH', { status }),
      onSuccess: (result) => {
        ordersBeforeMove.current.set(result.task.id, result.task.order);
        const updated = result.progress.goals[goalId.current];
        if (updated !== undefined) setGoalProgress(updated);
      },
      onFailure: (taskId, confirmed, caught) => {
        if (caught instanceof ApiError && caught.status === 404) {
          setTasks((current) => current.filter((task) => task.id !== taskId));
          setError('다른 곳에서 삭제된 할 일입니다.');
          return;
        }
        setTasks((current) =>
          current.map((task) =>
            task.id === taskId
              ? {
                  ...task,
                  status: confirmed,
                  order: ordersBeforeMove.current.get(taskId) ?? task.order,
                }
              : task,
          ),
        );
        setError(`상태를 저장하지 못해 되돌렸습니다. ${(caught as Error).message}`);
      },
      onIdle: () => {
        ordersBeforeMove.current.clear();
        void load();
      },
    });
  }, [load]);

  useEffect(() => {
    void load();
  }, [load]);

  function moveTask(task: Task, status: TaskStatus) {
    setError('');
    if (!ordersBeforeMove.current.has(task.id)) ordersBeforeMove.current.set(task.id, task.order);
    setTasks((current) =>
      current.map((candidate) =>
        candidate.id === task.id ? { ...candidate, status, order: Date.now() } : candidate,
      ),
    );
    queue.current?.enqueue(task.id, task.status, status);
  }

  async function saved() {
    setDialog(null);
    await load();
  }

  async function carryOver(createIfMissing: boolean) {
    try {
      const result = await api<CarryOverResult>(`/api/weeks/${id}/carry-over`, 'POST', {
        createIfMissing,
      });
      setDialog(null);
      setNotice(`미완료 할 일 ${result.movedCount}개를 다음 주로 옮겼습니다.`);
    } finally {
      // 시간 초과여도 서버는 옮겼을 수 있어 항상 다시 불러온다.
      await load();
    }
  }

  async function requestCarryOver() {
    setError('');
    setNotice('');
    if (queue.current?.isBusy()) {
      setError('카드 저장이 끝난 뒤 다시 시도하세요.');
      return;
    }
    try {
      await carryOver(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.body.nextWeekMissing) {
        setDialog({ kind: 'createNextWeek' });
      } else {
        setError((caught as Error).message);
      }
    }
  }

  if (!week) {
    return error ? (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    ) : (
      <p className="text-sm text-slate-600">불러오는 중…</p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Link href={`/goals/${week.goalId}`} className="text-sm text-indigo-700 hover:underline">
        ← {week.goalTitle}
      </Link>
      <div className="card flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{week.title}</h1>
          <span className="text-sm text-slate-500">
            {week.startDate} ~ {week.endDate}
          </span>
        </div>
        <div data-testid="week-progress" className="flex items-center gap-3">
          <span className="w-20 text-sm text-slate-600">주간 진행률</span>
          <div className="flex-1">
            <ProgressBar value={calcProgress(tasks)} label="주간 진행률" />
          </div>
        </div>
        <div data-testid="goal-progress" className="flex items-center gap-3">
          <span className="w-20 text-sm text-slate-600">목표 진행률</span>
          <div className="flex-1">
            <ProgressBar value={goalProgress} label="목표 진행률" />
          </div>
        </div>
      </div>
      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
          {notice}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <button className="btn" onClick={requestCarryOver}>
          미완료 할 일 다음 주로 이동
        </button>
        <button className="btn-primary" onClick={() => setDialog({ kind: 'form' })}>
          새 할 일
        </button>
      </div>
      <Board
        tasks={tasks}
        onMove={moveTask}
        onEdit={(task) => setDialog({ kind: 'form', task })}
        onDelete={(task) => setDialog({ kind: 'delete', task })}
      />
      {dialog?.kind === 'form' && (
        <TaskForm
          weekId={week.id}
          defaultDate={week.startDate}
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
            await saved();
          }}
        />
      )}
      {dialog?.kind === 'createNextWeek' && (
        <Modal
          title="다음 주 계획 만들기"
          submitLabel="만들고 이동"
          onClose={() => setDialog(null)}
          onSubmit={() => carryOver(true)}
        >
          <p className="text-sm">다음 주 계획이 없습니다. 새로 만들어 미완료 할 일을 옮길까요?</p>
        </Modal>
      )}
    </div>
  );
}
