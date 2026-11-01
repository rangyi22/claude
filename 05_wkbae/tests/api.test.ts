import { MongoMemoryServer } from 'mongodb-memory-server';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { GET as goalsGET, POST as goalsPOST } from '@/app/api/goals/route';
import {
  DELETE as goalDELETE,
  GET as goalGET,
  PATCH as goalPATCH,
} from '@/app/api/goals/[id]/route';
import { GET as summaryGET } from '@/app/api/summary/route';
import { GET as tasksGET, POST as tasksPOST } from '@/app/api/tasks/route';
import { DELETE as taskDELETE, PATCH as taskPATCH } from '@/app/api/tasks/[id]/route';
import { POST as weeksPOST } from '@/app/api/weeks/route';
import {
  DELETE as weekDELETE,
  GET as weekGET,
  PATCH as weekPATCH,
} from '@/app/api/weeks/[id]/route';
import { POST as carryPOST } from '@/app/api/weeks/[id]/carry-over/route';
import { closeDb, getDb } from '@/lib/db';
import type { Goal, GoalDetail, Task, TaskMutationResult, Week, WeekDetail } from '@/lib/types';

let mongo: MongoMemoryServer;

function request(method: string, body?: unknown, url = 'http://test/api') {
  return new Request(url, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function ctx(id: string) {
  return { params: Promise.resolve({ id }) };
}

async function ok<T>(response: Response): Promise<T> {
  expect(response.status).toBeLessThan(300);
  return response.json() as Promise<T>;
}

async function makeGoal(): Promise<Goal> {
  return ok(await goalsPOST(request('POST', { title: '건강', year: 2026 })));
}

async function makeWeek(goalId: string, startDate = '2026-11-02', endDate = '2026-11-08') {
  return ok<Week>(await weeksPOST(request('POST', { goalId, title: '1주', startDate, endDate })));
}

async function makeTask(weekId: string, weight = 1, date = '2026-11-03'): Promise<Task> {
  const created = await tasksPOST(request('POST', { weekId, title: '달리기', date, weight }));
  return (await ok<TaskMutationResult>(created)).task;
}

async function setStatus(id: string, status: string) {
  return ok<TaskMutationResult>(await taskPATCH(request('PATCH', { status }), ctx(id)));
}

async function goalProgress(id: string) {
  return (await ok<GoalDetail>(await goalGET(request('GET'), ctx(id)))).progress;
}

async function weekDetail(id: string) {
  return ok<WeekDetail>(await weekGET(request('GET'), ctx(id)));
}

beforeAll(async () => {
  mongo = await MongoMemoryServer.create();
  process.env.MONGODB_URI = mongo.getUri();
});

afterAll(async () => {
  await closeDb();
  await mongo.stop();
});

beforeEach(async () => {
  const db = await getDb();
  await Promise.all(['goals', 'weeks', 'tasks'].map((name) => db.collection(name).deleteMany({})));
});

describe('연결 필수와 입력 검증', () => {
  it('AC 2: 상위 없이 만들면 400', async () => {
    const week = await weeksPOST(
      request('POST', { title: 't', startDate: '2026-11-02', endDate: '2026-11-08' }),
    );
    expect(week.status).toBe(400);
    const task = await tasksPOST(request('POST', { title: 't', date: '2026-11-02' }));
    expect(task.status).toBe(400);
    expect((await task.json()).error).toContain('주간 계획');
  });

  it('존재하지 않는 상위로 만들면 400', async () => {
    const missing = '0123456789abcdef01234567';
    const week = await weeksPOST(
      request('POST', {
        goalId: missing,
        title: 't',
        startDate: '2026-11-02',
        endDate: '2026-11-08',
      }),
    );
    expect(week.status).toBe(400);
    const task = await tasksPOST(
      request('POST', { weekId: 'not-an-id', title: 't', date: '2026-11-02' }),
    );
    expect(task.status).toBe(400);
  });

  it('AC 3: 가중치 기본값과 신규 상태', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const bad = await tasksPOST(
      request('POST', { weekId: week.id, title: 't', date: '2026-11-03', weight: 6 }),
    );
    expect(bad.status).toBe(400);
    const created = await tasksPOST(
      request('POST', { weekId: week.id, title: 't', date: '2026-11-03' }),
    );
    const { task } = await ok<TaskMutationResult>(created);
    expect(task).toMatchObject({ weight: 1, status: 'todo' });
  });

  it('알 수 없는 ID는 404, 잘못된 JSON은 400', async () => {
    expect((await goalGET(request('GET'), ctx('nope'))).status).toBe(404);
    const malformed = new Request('http://test/api', { method: 'POST', body: '{' });
    expect((await goalsPOST(malformed)).status).toBe(400);
    const missing = '0123456789abcdef01234567';
    expect((await taskPATCH(request('PATCH', { status: 'done' }), ctx(missing))).status).toBe(404);
    expect((await taskDELETE(request('DELETE'), ctx(missing))).status).toBe(404);
  });

  it.each([{ weight: 0 }, { status: 'x' }, { weekId: '' }, { date: 'x' }, { userId: 'a' }])(
    '잘못된 PATCH %j는 400이고 데이터가 그대로다',
    async (body) => {
      const goal = await makeGoal();
      const week = await makeWeek(goal.id);
      const task = await makeTask(week.id, 2);
      expect((await taskPATCH(request('PATCH', body), ctx(task.id))).status).toBe(400);
      expect((await weekDetail(week.id)).tasks[0]).toEqual(task);
    },
  );

  it('잘못된 날짜 쿼리는 400이다', async () => {
    const tasks = await tasksGET(request('GET', undefined, 'http://test/api?from=garbage'));
    expect(tasks.status).toBe(400);
    const summary = await summaryGET(request('GET', undefined, 'http://test/api?today=garbage'));
    expect(summary.status).toBe(400);
  });

  it('CRUD로 수정한 값이 조회된다', async () => {
    const goal = await makeGoal();
    await ok(await goalPATCH(request('PATCH', { title: '체력' }), ctx(goal.id)));
    const list = await ok<Goal[]>(await goalsGET());
    expect(list).toHaveLength(1);
    expect(list[0]).toMatchObject({ title: '체력', weekCount: 0, progress: 0 });
  });
});

describe('진행률', () => {
  it('AC 5, 6: 가중치 기준으로 주간과 목표 진행률을 계산한다', async () => {
    const goal = await makeGoal();
    const weekA = await makeWeek(goal.id);
    const weekB = await makeWeek(goal.id, '2026-11-09', '2026-11-15');
    const two = await makeTask(weekA.id, 2);
    await makeTask(weekA.id, 3);
    const five = await makeTask(weekB.id, 5, '2026-11-10');

    const { progress } = await setStatus(two.id, 'done');
    expect(progress.weeks[weekA.id]).toBe(40);

    await setStatus(five.id, 'done');
    expect(await goalProgress(goal.id)).toBe(70);
    expect((await weekDetail(weekA.id)).goalProgress).toBe(70);
  });

  it('AC 7: 할 일을 삭제하면 재계산된다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const done = await makeTask(week.id, 2);
    const todo = await makeTask(week.id, 3);
    await setStatus(done.id, 'done');

    const response = await taskDELETE(request('DELETE'), ctx(todo.id));
    const progress = await ok<TaskMutationResult['progress']>(response);
    expect(progress.weeks[week.id]).toBe(100);
    expect(progress.goals[goal.id]).toBe(100);
  });

  it('AC 10: 빈 주간은 0이고 목표 진행률을 바꾸지 않는다', async () => {
    const goal = await makeGoal();
    expect(await goalProgress(goal.id)).toBe(0);
    const week = await makeWeek(goal.id);
    expect((await weekDetail(week.id)).progress).toBe(0);

    const task = await makeTask(week.id, 2);
    await setStatus(task.id, 'done');
    await makeWeek(goal.id, '2026-11-09', '2026-11-15');
    expect(await goalProgress(goal.id)).toBe(100);
  });

  it('AC 13: 다른 주간으로 옮기면 양쪽 진행률이 바뀐다', async () => {
    const goalA = await makeGoal();
    const goalB = await makeGoal();
    const weekA = await makeWeek(goalA.id);
    const weekB = await makeWeek(goalB.id);
    const moved = await makeTask(weekA.id, 1);
    await makeTask(weekA.id, 1);
    await setStatus(moved.id, 'done');
    expect(await goalProgress(goalA.id)).toBe(50);

    const response = await taskPATCH(request('PATCH', { weekId: weekB.id }), ctx(moved.id));
    const { progress } = await ok<TaskMutationResult>(response);
    expect(progress.weeks).toEqual({ [weekA.id]: 0, [weekB.id]: 100 });
    expect(progress.goals).toEqual({ [goalA.id]: 0, [goalB.id]: 100 });
  });
});

describe('삭제 정책', () => {
  it('AC 8: 하위가 있으면 409와 개수를 주고 데이터가 변하지 않는다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    await makeTask(week.id);

    const goalResponse = await goalDELETE(request('DELETE'), ctx(goal.id));
    expect(goalResponse.status).toBe(409);
    expect(await goalResponse.json()).toMatchObject({ childCount: 1 });

    const weekResponse = await weekDELETE(request('DELETE'), ctx(week.id));
    expect(weekResponse.status).toBe(409);
    expect(await weekResponse.json()).toMatchObject({ childCount: 1 });

    expect((await weekDetail(week.id)).tasks).toHaveLength(1);
    expect((await goalGET(request('GET'), ctx(goal.id))).status).toBe(200);
  });

  it('AC 8: 하위가 없으면 삭제되고 빈 주간 삭제는 목표 진행률을 바꾸지 않는다', async () => {
    const goal = await makeGoal();
    const full = await makeWeek(goal.id);
    const empty = await makeWeek(goal.id, '2026-11-09', '2026-11-15');
    const task = await makeTask(full.id);
    await setStatus(task.id, 'done');

    expect((await weekDELETE(request('DELETE'), ctx(empty.id))).status).toBe(200);
    expect(await goalProgress(goal.id)).toBe(100);

    await taskDELETE(request('DELETE'), ctx(task.id));
    expect((await weekDELETE(request('DELETE'), ctx(full.id))).status).toBe(200);
    expect((await goalDELETE(request('DELETE'), ctx(goal.id))).status).toBe(200);
  });
});

describe('날짜 범위', () => {
  it('AC 11: 기간 밖 날짜는 생성·수정이 거부된다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const outside = await tasksPOST(
      request('POST', { weekId: week.id, title: 't', date: '2026-11-09' }),
    );
    expect(outside.status).toBe(400);

    const task = await makeTask(week.id);
    const moved = await taskPATCH(request('PATCH', { date: '2026-11-01' }), ctx(task.id));
    expect(moved.status).toBe(400);
    expect((await weekDetail(week.id)).tasks[0].date).toBe('2026-11-03');
  });

  it('AC 11: 주간을 바꿀 때 날짜가 새 기간 밖이면 거부된다', async () => {
    const goal = await makeGoal();
    const weekA = await makeWeek(goal.id);
    const weekB = await makeWeek(goal.id, '2026-11-09', '2026-11-15');
    const task = await makeTask(weekA.id);
    const rejected = await taskPATCH(request('PATCH', { weekId: weekB.id }), ctx(task.id));
    expect(rejected.status).toBe(400);
    const accepted = await taskPATCH(
      request('PATCH', { weekId: weekB.id, date: '2026-11-10' }),
      ctx(task.id),
    );
    expect(accepted.status).toBe(200);
  });

  it('AC 12: 기간을 줄여 할 일이 벗어나면 409로 거부된다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    await makeTask(week.id, 1, '2026-11-07');

    const response = await weekPATCH(request('PATCH', { endDate: '2026-11-06' }), ctx(week.id));
    expect(response.status).toBe(409);
    expect((await weekDetail(week.id)).endDate).toBe('2026-11-08');

    expect(
      (await weekPATCH(request('PATCH', { endDate: '2026-11-07' }), ctx(week.id))).status,
    ).toBe(200);
    expect(
      (await weekPATCH(request('PATCH', { startDate: '2026-12-01' }), ctx(week.id))).status,
    ).toBe(400);
  });
});

describe('순서와 필터', () => {
  it('상태를 바꾸면 새 컬럼 마지막에 들어간다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const first = await makeTask(week.id);
    const second = await makeTask(week.id);
    await setStatus(first.id, 'doing');
    const { task } = await setStatus(second.id, 'doing');
    expect(task.order).toBeGreaterThan(1);
  });

  it('날짜 범위로 할 일을 조회한다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    await makeTask(week.id, 1, '2026-11-03');
    await makeTask(week.id, 1, '2026-11-05');
    const url = 'http://test/api?from=2026-11-04&to=2026-11-06';
    const tasks = await ok<Task[]>(await tasksGET(request('GET', undefined, url)));
    expect(tasks.map((task) => task.date)).toEqual(['2026-11-05']);
  });

  it('인덱스가 생성된다', async () => {
    const db = await getDb();
    const tasks = (await db.collection('tasks').indexes()).map((index) => index.name);
    const weeks = (await db.collection('weeks').indexes()).map((index) => index.name);
    expect(tasks).toEqual(
      expect.arrayContaining(['weekId_1', 'weekId_1_status_1_order_1', 'date_1']),
    );
    expect(weeks).toContain('goalId_1');
  });
});

describe('미완료 할 일 다음 주 이동', () => {
  it('AC 16: 다음 주가 없으면 409로 알리고 데이터를 바꾸지 않는다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    await makeTask(week.id);
    const response = await carryPOST(request('POST', {}), ctx(week.id));
    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({ nextWeekMissing: true });
    expect((await weekDetail(week.id)).tasks).toHaveLength(1);
  });

  it('AC 16: 요청하면 다음 주를 만들어 미완료만 +7일로 옮긴다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const pending = await makeTask(week.id, 1, '2026-11-03');
    const done = await makeTask(week.id, 1, '2026-11-04');
    await setStatus(done.id, 'done');

    const response = await carryPOST(request('POST', { createIfMissing: true }), ctx(week.id));
    const result = await ok<{ weekId: string; movedCount: number }>(response);
    expect(result.movedCount).toBe(1);

    const next = await weekDetail(result.weekId);
    expect(next).toMatchObject({ startDate: '2026-11-09', endDate: '2026-11-15' });
    expect(next.tasks.map((task) => [task.id, task.date])).toEqual([[pending.id, '2026-11-10']]);
    expect((await weekDetail(week.id)).tasks.map((task) => task.id)).toEqual([done.id]);
  });

  it('미완료 할 일이 없으면 다음 주를 만들지 않는다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const response = await carryPOST(request('POST', { createIfMissing: true }), ctx(week.id));
    expect(await ok(response)).toEqual({ weekId: week.id, movedCount: 0 });
    expect((await ok<GoalDetail>(await goalGET(request('GET'), ctx(goal.id)))).weeks).toHaveLength(
      1,
    );
  });

  it('AC 16: 기존 다음 주 카드 뒤에 상태별로 이어 붙인다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const next = await makeWeek(goal.id, '2026-11-09', '2026-11-15');
    const existing = await makeTask(next.id, 1, '2026-11-10');
    await makeTask(week.id);
    await makeTask(week.id);

    await ok(await carryPOST(request('POST', {}), ctx(week.id)));
    const orders = (await weekDetail(next.id)).tasks.map((task) => task.order);
    expect(orders.sort()).toEqual([existing.order, existing.order + 1, existing.order + 2]);
  });

  it('AC 16: 새 기간을 벗어나면 가까운 날짜로 맞춘다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    await makeTask(week.id, 1, '2026-11-08');
    const next = await makeWeek(goal.id, '2026-11-09', '2026-11-13');

    await ok(await carryPOST(request('POST', {}), ctx(week.id)));
    expect((await weekDetail(next.id)).tasks[0].date).toBe('2026-11-13');
  });
});

describe('요약', () => {
  it('성공 지표와 목표별 현황을 준다', async () => {
    const goal = await makeGoal();
    const week = await makeWeek(goal.id);
    const task = await makeTask(week.id);
    await setStatus(task.id, 'done');

    const response = await summaryGET(
      request('GET', undefined, 'http://test/api?today=2026-11-04'),
    );
    const summary = await ok<{
      metrics: { planStreak: number; completionRate: number };
      goals: GoalDetail[];
    }>(response);
    expect(summary.metrics).toEqual({ planStreak: 1, completionRate: 100 });
    expect(summary.goals[0].weeks[0].progress).toBe(100);
  });
});
