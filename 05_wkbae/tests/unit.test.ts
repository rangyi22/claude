import { describe, expect, it, vi } from 'vitest';
import { addDays, clampDate, isValidDate, mondayOf } from '@/lib/dates';
import { calcMetrics } from '@/lib/metrics';
import { createMoveQueue } from '@/lib/moveQueue';
import { periodRange } from '@/lib/period';
import { calcProgress } from '@/lib/progress';
import type { TaskStatus } from '@/lib/types';
import { taskCreateSchema, weekCreateSchema } from '@/lib/validation';

describe('calcProgress', () => {
  it('AC 5: 가중치 [2, 3] 중 2가 done이면 40%', () => {
    expect(
      calcProgress([
        { weight: 2, status: 'done' },
        { weight: 3, status: 'todo' },
      ]),
    ).toBe(40);
  });

  it('AC 6: 주간 A(합 5, done 2)와 B(합 5, done 5)를 합치면 70%', () => {
    expect(
      calcProgress([
        { weight: 2, status: 'done' },
        { weight: 3, status: 'doing' },
        { weight: 5, status: 'done' },
      ]),
    ).toBe(70);
  });

  it('AC 10: 할 일이 없으면 0%', () => {
    expect(calcProgress([])).toBe(0);
  });
});

describe('할 일 검증', () => {
  const base = { weekId: 'w', title: '운동', date: '2026-11-02' };

  it('AC 3: 가중치를 생략하면 1이다', () => {
    expect(taskCreateSchema.parse(base).weight).toBe(1);
  });

  it.each([0, 6, 1.5, '3'])('AC 3: 가중치 %s는 거부한다', (weight) => {
    expect(taskCreateSchema.safeParse({ ...base, weight }).success).toBe(false);
  });

  it('AC 2: 주간 계획이 없으면 거부한다', () => {
    expect(taskCreateSchema.safeParse({ title: 'x', date: '2026-11-02' }).success).toBe(false);
  });

  it('없는 달력 날짜는 거부한다', () => {
    expect(taskCreateSchema.safeParse({ ...base, date: '2026-02-30' }).success).toBe(false);
  });
});

describe('주간 계획 검증', () => {
  it('시작일이 종료일보다 늦으면 거부한다', () => {
    const week = { goalId: 'g', title: 't', startDate: '2026-11-08', endDate: '2026-11-02' };
    expect(weekCreateSchema.safeParse(week).success).toBe(false);
    expect(weekCreateSchema.safeParse({ ...week, endDate: '2026-11-08' }).success).toBe(true);
  });
});

describe('날짜 유틸', () => {
  it('형식과 달력을 함께 검사한다', () => {
    expect(isValidDate('2028-02-29')).toBe(true);
    expect(isValidDate('2026-2-3')).toBe(false);
  });

  it('월말을 넘겨 더한다', () => {
    expect(addDays('2026-12-28', 7)).toBe('2027-01-04');
  });

  it('월요일을 찾는다', () => {
    expect(mondayOf('2026-11-08')).toBe('2026-11-02');
    expect(mondayOf('2026-11-02')).toBe('2026-11-02');
  });

  it('범위로 맞춘다', () => {
    expect(clampDate('2026-11-01', '2026-11-02', '2026-11-08')).toBe('2026-11-02');
    expect(clampDate('2026-11-09', '2026-11-02', '2026-11-08')).toBe('2026-11-08');
  });
});

describe('periodRange', () => {
  it('일일/주간/연간 범위를 계산한다', () => {
    expect(periodRange('day', '2026-11-04')).toEqual({ from: '2026-11-04', to: '2026-11-04' });
    expect(periodRange('week', '2026-11-04')).toEqual({ from: '2026-11-02', to: '2026-11-08' });
    expect(periodRange('year', '2026-11-04')).toEqual({ from: '2026-01-01', to: '2026-12-31' });
  });
});

describe('calcMetrics', () => {
  function week(startDate: string, progress: number, taskCount = 1) {
    return { startDate, progress, taskCount };
  }

  it('연속 주를 세고 빈 주에서 끊는다', () => {
    const weeks = [
      week('2026-10-05', 100),
      week('2026-10-19', 50),
      week('2026-10-26', 50),
      week('2026-11-02', 50),
    ];
    expect(calcMetrics(weeks, '2026-11-04').planStreak).toBe(3);
  });

  it('이번 주 계획이 없어도 지난주까지의 기록을 유지한다', () => {
    expect(calcMetrics([week('2026-10-26', 50)], '2026-11-04').planStreak).toBe(1);
  });

  it('할 일이 없는 주는 세지 않는다', () => {
    expect(calcMetrics([week('2026-11-02', 0, 0)], '2026-11-04')).toEqual({
      planStreak: 0,
      completionRate: 0,
    });
  });

  it('오래된 계획은 완료율에 넣지 않는다', () => {
    expect(calcMetrics([week('2026-01-05', 100)], '2026-11-04').completionRate).toBe(0);
  });

  it('같은 주의 여러 계획은 달력 4주 안에서 함께 평균낸다', () => {
    const weeks = [
      week('2026-10-05', 100),
      week('2026-10-12', 100),
      week('2026-10-12', 0),
      week('2026-11-02', 50),
      week('2026-11-02', 50),
    ];
    expect(calcMetrics(weeks, '2026-11-04').completionRate).toBe(50);
  });

  it('완료율은 최근 4주 평균이다', () => {
    const weeks = [
      week('2026-10-05', 0),
      week('2026-10-12', 40),
      week('2026-10-19', 60),
      week('2026-10-26', 80),
      week('2026-11-02', 100),
    ];
    expect(calcMetrics(weeks, '2026-11-04').completionRate).toBe(70);
  });
});

describe('createMoveQueue', () => {
  function deferred() {
    const calls: { status: TaskStatus; resolve: () => void; reject: (e: Error) => void }[] = [];
    function send(_id: string, status: TaskStatus) {
      return new Promise<TaskStatus>((resolve, reject) => {
        calls.push({ status, resolve: () => resolve(status), reject });
      });
    }
    return { calls, send };
  }

  async function flush() {
    await new Promise((resolve) => setTimeout(resolve));
  }

  it('AC 14: 같은 카드는 앞 요청이 끝나야 다음을 보낸다', async () => {
    const { calls, send } = deferred();
    const onIdle = vi.fn();
    const onSuccess = vi.fn();
    const queue = createMoveQueue({ send, onSuccess, onFailure: vi.fn(), onIdle });

    queue.enqueue('a', 'todo', 'doing');
    queue.enqueue('a', 'doing', 'done');
    expect(calls.map((call) => call.status)).toEqual(['doing']);

    calls[0].resolve();
    await flush();
    expect(calls.map((call) => call.status)).toEqual(['doing', 'done']);
    expect(onIdle).not.toHaveBeenCalled();

    calls[1].resolve();
    await flush();
    expect(onSuccess).toHaveBeenLastCalledWith('done');
    expect(onIdle).toHaveBeenCalledOnce();
  });

  it('AC 4: 실패하면 마지막 확정 상태를 넘기고 대기 이동을 버린다', async () => {
    const { calls, send } = deferred();
    const onFailure = vi.fn();
    const queue = createMoveQueue({ send, onSuccess: vi.fn(), onFailure, onIdle: vi.fn() });

    queue.enqueue('a', 'todo', 'doing');
    queue.enqueue('a', 'doing', 'done');
    calls[0].reject(new Error('down'));
    await flush();

    expect(calls).toHaveLength(1);
    expect(onFailure).toHaveBeenCalledWith('a', 'todo', expect.any(Error));
  });

  it('다른 카드는 서로 기다리지 않는다', () => {
    const { calls, send } = deferred();
    const queue = createMoveQueue({
      send,
      onSuccess: vi.fn(),
      onFailure: vi.fn(),
      onIdle: vi.fn(),
    });

    queue.enqueue('a', 'todo', 'doing');
    queue.enqueue('b', 'todo', 'done');
    expect(calls).toHaveLength(2);
  });

  it('isBusy는 모든 카드가 끝나야 false다', async () => {
    const { calls, send } = deferred();
    const queue = createMoveQueue({
      send,
      onSuccess: vi.fn(),
      onFailure: vi.fn(),
      onIdle: vi.fn(),
    });

    queue.enqueue('a', 'todo', 'doing');
    queue.enqueue('b', 'todo', 'done');
    calls[0].reject(new Error('down'));
    await flush();
    expect(queue.isBusy()).toBe(true);

    calls[1].resolve();
    await flush();
    expect(queue.isBusy()).toBe(false);
  });
});
