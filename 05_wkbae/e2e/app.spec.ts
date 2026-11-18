import { expect, test, type Locator, type Page } from '@playwright/test';

function unique() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function alert(page: Page) {
  return page.getByRole('main').getByRole('alert');
}

async function seed(page: Page, weights: number[] = [2, 3]) {
  const name = unique();
  async function post(url: string, data: unknown) {
    return (await page.request.post(url, { data })).json();
  }
  const goal = await post('/api/goals', { title: `목표 ${name}`, year: 2026 });
  const week = await post('/api/weeks', {
    goalId: goal.id,
    title: `주간 ${name}`,
    startDate: '2026-11-02',
    endDate: '2026-11-08',
  });
  const tasks = [];
  for (const [index, weight] of weights.entries()) {
    const { task } = await post('/api/tasks', {
      weekId: week.id,
      title: `일 ${index + 1}`,
      date: '2026-11-03',
      weight,
    });
    tasks.push(task);
  }
  return { goal, week, tasks };
}

function card(page: Page, title: string): Locator {
  return page.getByTestId('task-card').filter({ hasText: title });
}

async function drag(page: Page, from: Locator, to: Locator) {
  const source = (await from.boundingBox())!;
  const target = (await to.boundingBox())!;
  await page.mouse.move(source.x + source.width / 2, source.y + 12);
  await page.mouse.down();
  await page.mouse.move(source.x + source.width / 2 + 10, source.y + 12, { steps: 3 });
  await page.mouse.move(target.x + target.width / 2, target.y + target.height / 2, { steps: 8 });
  await page.mouse.up();
  // dnd-kit은 드롭 직후 잠깐 클릭을 막는다.
  await page.waitForTimeout(100);
}

async function expectProgress(page: Page, testId: string, value: number) {
  await expect(page.getByTestId(testId).getByRole('progressbar')).toHaveAttribute(
    'aria-valuenow',
    String(value),
  );
}

function column(page: Page, status: string) {
  return page.getByTestId(`column-${status}`);
}

test('목표 → 주간 → 할 일을 화면에서 만들고 드래그하면 진행률이 유지된다 (AC 1, 4, 5, 7, 9)', async ({
  page,
}) => {
  const name = unique();
  await page.goto('/goals');
  await page.getByRole('button', { name: '새 Schedule' }).click();
  await page.getByLabel('제목').fill(`화면 목표 ${name}`);
  await page.getByRole('button', { name: '저장' }).click();
  await page.getByRole('link', { name: `화면 목표 ${name}` }).click();

  await page.getByRole('button', { name: '새 주간 계획' }).click();
  await page.getByLabel('제목').fill('첫 주');
  await page.getByLabel('시작일').fill('2026-11-02');
  await page.getByLabel('종료일').fill('2026-11-08');
  await page.getByRole('button', { name: '저장' }).click();
  await page.getByRole('link', { name: '첫 주' }).click();

  for (const [title, weight] of [
    ['가벼운 일', '2'],
    ['무거운 일', '3'],
  ]) {
    await page.getByRole('button', { name: '새 할 일' }).click();
    await page.getByLabel('제목').fill(title);
    await page.getByRole('dialog').getByLabel('가중치').selectOption(weight);
    await page.getByRole('button', { name: '저장' }).click();
    await expect(card(page, title)).toBeVisible();
  }
  await expectProgress(page, 'week-progress', 0);

  await drag(page, card(page, '가벼운 일'), column(page, 'done'));
  await expect(column(page, 'done')).toContainText('가벼운 일');
  await expectProgress(page, 'week-progress', 40);
  await expectProgress(page, 'goal-progress', 40);

  await page.reload();
  await expect(column(page, 'done')).toContainText('가벼운 일');
  await expectProgress(page, 'week-progress', 40);

  await card(page, '무거운 일').getByRole('button', { name: '삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(card(page, '무거운 일')).toHaveCount(0);
  await expectProgress(page, 'week-progress', 100);
  await expectProgress(page, 'goal-progress', 100);
});

test('저장에 실패하면 카드와 진행률이 되돌아가고 오류가 보인다 (AC 4)', async ({ page }) => {
  const { week } = await seed(page);
  await page.route('**/api/tasks/*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500));
    await route.fulfill({ status: 500, body: '{}' });
  });
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'done'));
  await expectProgress(page, 'week-progress', 40);
  await expect(alert(page)).toContainText('되돌렸습니다');
  await expect(column(page, 'todo')).toContainText('일 1');
  await expectProgress(page, 'week-progress', 0);
  await expectProgress(page, 'goal-progress', 0);
});

test('저장 중 다른 조회가 끝나도 옮긴 카드가 되돌아가지 않는다', async ({ page }) => {
  const { week } = await seed(page);
  await page.route('**/api/tasks/*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    await route.continue();
  });
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'done'));
  await page.getByRole('button', { name: '새 할 일' }).click();
  await page.getByLabel('제목').fill('저장 중 추가');
  await page.getByRole('button', { name: '저장' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.waitForTimeout(500);
  await expect(card(page, '저장 중 추가')).toHaveCount(0);
  expect(await column(page, 'done').textContent()).toContain('일 1');

  await expect(card(page, '저장 중 추가')).toBeVisible();
  await expect(column(page, 'done')).toContainText('일 1');
});

test('저장 중에는 다음 주 이동을 막는다', async ({ page }) => {
  const { week } = await seed(page);
  await page.route('**/api/tasks/*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    await route.continue();
  });
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'done'));
  await page.getByRole('button', { name: '미완료 할 일 다음 주로 이동' }).click();
  await expect(alert(page)).toContainText('저장이 끝난 뒤');
});

test('네트워크 오류여도 되돌아간다 (AC 4)', async ({ page }) => {
  const { week } = await seed(page);
  await page.route('**/api/tasks/*', (route) => route.abort());
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'doing'));
  await expect(alert(page)).toContainText('되돌렸습니다');
  await expect(column(page, 'todo')).toContainText('일 1');
});

test('5초 안에 응답이 없으면 되돌아간다 (AC 4)', async ({ page }) => {
  const { week } = await seed(page);
  await page.route('**/api/tasks/*', () => undefined);
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'done'));
  await expect(column(page, 'done')).toContainText('일 1');
  await expect(alert(page)).toContainText('되돌렸습니다', { timeout: 7_000 });
  await expect(column(page, 'todo')).toContainText('일 1');
});

test('같은 카드를 연속으로 옮기면 순서대로 보내고 마지막 위치가 저장된다 (AC 14)', async ({
  page,
}) => {
  const { week } = await seed(page);
  const statuses: string[] = [];
  let active = 0;
  let maxActive = 0;
  await page.route('**/api/tasks/*', async (route) => {
    active += 1;
    maxActive = Math.max(maxActive, active);
    statuses.push(route.request().postDataJSON().status);
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.continue();
    active -= 1;
  });
  await page.goto(`/weeks/${week.id}`);

  await drag(page, card(page, '일 1'), column(page, 'doing'));
  await expect(column(page, 'doing')).toContainText('일 1');
  await drag(page, card(page, '일 1'), column(page, 'done'));
  await expect(column(page, 'done')).toContainText('일 1');

  await expect.poll(() => statuses).toEqual(['doing', 'done']);
  expect(maxActive).toBe(1);
  await page.waitForTimeout(800);
  await page.reload();
  await expect(column(page, 'done')).toContainText('일 1');
});

test('다른 탭에서 삭제된 할 일을 옮기면 카드가 사라지고 안내가 보인다 (AC 14)', async ({
  page,
}) => {
  const { week, tasks } = await seed(page);
  await page.goto(`/weeks/${week.id}`);
  await expect(card(page, '일 1')).toBeVisible();
  await page.request.delete(`/api/tasks/${tasks[0].id}`);

  await drag(page, card(page, '일 1'), column(page, 'done'));
  await expect(alert(page)).toContainText('삭제된 할 일');
  await expect(card(page, '일 1')).toHaveCount(0);
});

test('키보드로 카드를 옮길 수 있다', async ({ page }) => {
  const { week } = await seed(page);
  await page.goto(`/weeks/${week.id}`);
  await card(page, '일 1').focus();
  for (const key of ['Space', 'ArrowRight', 'ArrowRight', 'Space']) {
    await page.keyboard.press(key);
    await page.waitForTimeout(150);
  }
  await expect(column(page, 'done')).toContainText('일 1');
  await expectProgress(page, 'week-progress', 40);
});

test('목표와 할 일을 수정하고, 하위가 있는 목표 삭제는 막는다 (AC 1, 8)', async ({ page }) => {
  const { goal, week } = await seed(page);
  await page.goto(`/weeks/${week.id}`);
  await card(page, '일 1').getByRole('button', { name: '수정' }).click();
  await page.getByLabel('제목').fill('고친 일');
  await page.getByRole('button', { name: '저장' }).click();
  await expect(card(page, '고친 일')).toBeVisible();

  await page.goto('/goals');
  const row = page.getByTestId('goal-card').filter({ hasText: goal.title });
  await row.getByRole('button', { name: '삭제', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(alert(page)).toContainText('주간 계획 1개');
  await page.getByRole('button', { name: '취소' }).click();

  await row.getByRole('button', { name: '수정', exact: true }).click();
  await page.getByLabel('제목').fill(`${goal.title} 수정`);
  await page.getByRole('button', { name: '저장' }).click();
  await expect(page.getByRole('link', { name: `${goal.title} 수정` })).toBeVisible();
});

test('삭제 차단과 기간 위반 사유가 화면에 보인다 (AC 8, 11, 12)', async ({ page }) => {
  const { goal, week } = await seed(page);

  await page.goto(`/goals/${goal.id}`);
  await page.getByTestId('week-card').getByRole('button', { name: '삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(alert(page)).toContainText('할 일 2개');
  await page.getByRole('button', { name: '취소' }).click();

  await page.getByTestId('week-card').getByRole('button', { name: '수정' }).click();
  await page.getByLabel('종료일').fill('2026-11-02');
  await page.getByRole('button', { name: '저장' }).click();
  await expect(alert(page)).toContainText('벗어나는 할 일 2개');
  await page.getByRole('button', { name: '취소' }).click();

  await page.goto(`/weeks/${week.id}`);
  await card(page, '일 1').getByRole('button', { name: '수정' }).click();
  await page.getByLabel('마감일').fill('2026-12-25');
  await page.getByRole('button', { name: '저장' }).click();
  await expect(alert(page)).toContainText('기간');
});

test('미완료 할 일을 다음 주로 옮긴다 (AC 16)', async ({ page }) => {
  const { goal, week } = await seed(page);
  await page.goto(`/weeks/${week.id}`);
  await page.getByRole('button', { name: '미완료 할 일 다음 주로 이동' }).click();
  await page.getByRole('button', { name: '만들고 이동' }).click();
  await expect(page.getByText('미완료 할 일 2개를 다음 주로 옮겼습니다.')).toBeVisible();
  await expect(page.getByTestId('task-card')).toHaveCount(0);

  await page.goto(`/goals/${goal.id}`);
  await expect(page.getByTestId('week-card')).toHaveCount(2);
  await expect(page.getByTestId('week-card').nth(1)).toContainText('할 일 2개');
});

test('기간 필터와 달성 현황이 보인다 (AC 16)', async ({ page }) => {
  const { goal } = await seed(page, [2]);
  await page.goto('/tasks');
  await page.getByLabel('기준 날짜').fill('2026-11-03');
  await expect(page.getByTestId('period-task').first()).toContainText('2026-11-03');
  await page.getByLabel('기준 날짜').fill('2026-11-04');
  await expect(page.getByText('이 기간의 할 일이 없습니다.')).toBeVisible();
  await page.getByRole('button', { name: '주간' }).click();
  await expect(page.getByTestId('period-task').first()).toBeVisible();

  await page.goto('/summary');
  await expect(page.getByTestId('metric-streak')).toBeVisible();
  await expect(page.getByTestId('metric-completion')).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(goal.title) })).toBeVisible();
  await expect(page.getByRole('progressbar').first()).toBeVisible();
});

test('기간별 보기에서 할 일을 수정하고 삭제한다 (일일, 주간)', async ({ page }) => {
  const name = unique();
  const { tasks } = await seed(page, [2, 3]);
  await page.request.patch(`/api/tasks/${tasks[0].id}`, { data: { title: `고칠일 ${name}` } });
  await page.request.patch(`/api/tasks/${tasks[1].id}`, { data: { title: `지울일 ${name}` } });
  function row(title: string) {
    return page.getByTestId('period-task').filter({ hasText: title });
  }

  await page.goto('/tasks');
  await page.getByLabel('기준 날짜').fill('2026-11-03');
  await row(`고칠일 ${name}`).getByRole('button', { name: '수정' }).click();
  await page.getByRole('dialog').getByLabel('제목').fill(`고친일 ${name}`);
  await page.getByRole('dialog').getByRole('button', { name: '저장' }).click();
  await expect(row(`고친일 ${name}`)).toBeVisible();
  await expect(row(`고칠일 ${name}`)).toHaveCount(0);

  await page.getByRole('button', { name: '주간', exact: true }).click();
  await row(`지울일 ${name}`).getByRole('button', { name: '삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(row(`지울일 ${name}`)).toHaveCount(0);
  await expect(row(`고친일 ${name}`)).toBeVisible();

  await page.reload();
  await page.getByLabel('기준 날짜').fill('2026-11-03');
  await expect(row(`지울일 ${name}`)).toHaveCount(0);
});

test('주간 보드에서 주간 계획을 수정하고, 할 일이 있으면 삭제를 막는다 (AC 8)', async ({
  page,
}) => {
  const name = unique();
  const { goal, week, tasks } = await seed(page);
  await page.goto(`/weeks/${week.id}`);

  await page.getByRole('button', { name: '주간 계획 수정' }).click();
  await page.getByRole('dialog').getByLabel('제목').fill(`고친주 ${name}`);
  await page.getByRole('dialog').getByRole('button', { name: '저장' }).click();
  await expect(page.getByRole('heading', { name: `고친주 ${name}` })).toBeVisible();

  await page.getByRole('button', { name: '주간 계획 삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('할 일 2개');
  await page.getByRole('button', { name: '취소' }).click();
  await expect(page.getByRole('heading', { name: `고친주 ${name}` })).toBeVisible();

  for (const task of tasks) await page.request.delete(`/api/tasks/${task.id}`);
  await page.reload();
  await page.getByRole('button', { name: '주간 계획 삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(page).toHaveURL(new RegExp(`/goals/${goal.id}$`));
  await expect(page.getByTestId('week-card')).toHaveCount(0);
});

test('할 일 관리 홈은 오늘의 할 일과 이번 주 계획을 보여 주고 목표 화면과 구분된다', async ({
  page,
}) => {
  const name = unique();
  const { goal, week, tasks } = await seed(page, [2, 3]);
  await page.request.patch(`/api/tasks/${tasks[0].id}`, {
    data: { title: `오늘일 ${name}`, status: 'done' },
  });
  await page.clock.setFixedTime(new Date('2026-11-03T12:00:00'));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: '할 일 관리', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Schedule', exact: true })).toHaveCount(0);
  await expect(page.getByTestId('today-task').filter({ hasText: `오늘일 ${name}` })).toBeVisible();

  const thisWeek = page.getByTestId('home-week').filter({ hasText: week.title });
  await expect(thisWeek).toContainText(goal.title);
  await expect(thisWeek.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
  await thisWeek.getByRole('link', { name: week.title }).click();
  await expect(page).toHaveURL(new RegExp(`/weeks/${week.id}$`));
});

test('메뉴는 화면마다 다른 곳으로 이동하고 현재 위치를 표시한다', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await page.goto('/');
  await expect(nav.getByRole('link', { name: '할 일 관리' })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(nav.getByRole('link', { name: 'Schedule', exact: true })).not.toHaveAttribute(
    'aria-current',
    'page',
  );

  await nav.getByRole('link', { name: 'Schedule', exact: true }).click();
  await expect(page).toHaveURL(/\/goals$/);
  await expect(page.getByRole('heading', { name: 'Schedule', exact: true })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Schedule', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(nav.getByRole('link', { name: '할 일 관리' })).not.toHaveAttribute(
    'aria-current',
    'page',
  );

  await nav.getByRole('link', { name: '할 일 관리' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: '할 일 관리', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Schedule', exact: true })).toHaveCount(0);
});

test('주간 보드는 목표 메뉴를 강조하고 목표 목록 링크가 /goals로 간다', async ({ page }) => {
  const { goal } = await seed(page);
  await page.goto(`/goals/${goal.id}`);
  await expect(
    page.getByRole('navigation').getByRole('link', { name: 'Schedule', exact: true }),
  ).toHaveAttribute('aria-current', 'page');
  await page.getByRole('link', { name: '← Schedule 목록' }).click();
  await expect(page).toHaveURL(/\/goals$/);
});

test('목표 화면에서 주간 계획을 추가·수정·삭제한다', async ({ page }) => {
  const name = unique();
  const goalResponse = await page.request.post('/api/goals', {
    data: { title: `주간목표 ${name}`, year: 2026 },
  });
  const goal = await goalResponse.json();
  await page.goto('/goals');
  const goalCard = page.getByTestId('goal-card').filter({ hasText: goal.title });
  const dialog = page.getByRole('dialog');
  await expect(goalCard.getByText('주간 계획이 없습니다.')).toBeVisible();

  await goalCard.getByRole('button', { name: '주간 계획 추가' }).click();
  await dialog.getByLabel('제목').fill(`잘못된주 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-11-20');
  await dialog.getByLabel('종료일').fill('2026-11-16');
  await dialog.getByRole('button', { name: '저장' }).click();
  await expect(dialog.getByRole('alert')).toContainText('시작일은 종료일보다');
  await dialog.getByRole('button', { name: '취소' }).click();
  await expect(goalCard.getByTestId('goal-week')).toHaveCount(0);

  await goalCard.getByRole('button', { name: '주간 계획 추가' }).click();
  await dialog.getByLabel('제목').fill(`첫주 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-11-09');
  await dialog.getByLabel('종료일').fill('2026-11-15');
  await dialog.getByRole('button', { name: '저장' }).click();
  const added = goalCard.getByTestId('goal-week').filter({ hasText: `첫주 ${name}` });
  await expect(added).toContainText('2026-11-09 ~ 2026-11-15');
  await expect(added.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  await expect(goalCard).toContainText('주간 계획 1개');

  await added.getByRole('button', { name: `첫주 ${name} 수정` }).click();
  await dialog.getByLabel('제목').fill(`둘째주 ${name}`);
  await dialog.getByLabel('종료일').fill('2026-11-16');
  await dialog.getByRole('button', { name: '저장' }).click();
  const edited = goalCard.getByTestId('goal-week').filter({ hasText: `둘째주 ${name}` });
  await expect(edited).toContainText('2026-11-09 ~ 2026-11-16');
  await page.reload();
  await expect(edited).toContainText('2026-11-09 ~ 2026-11-16');

  const weeks = await (await page.request.get(`/api/weeks?goalId=${goal.id}`)).json();
  const created = await page.request.post('/api/tasks', {
    data: { weekId: weeks[0].id, title: '구간 끝 일', date: '2026-11-16', weight: 1 },
  });
  const { task } = await created.json();

  await edited.getByRole('button', { name: `둘째주 ${name} 수정` }).click();
  await dialog.getByLabel('종료일').fill('2026-11-10');
  await dialog.getByRole('button', { name: '저장' }).click();
  await expect(dialog.getByRole('alert')).toContainText('벗어나는 할 일 1개');
  await dialog.getByRole('button', { name: '취소' }).click();
  await expect(edited).toContainText('2026-11-09 ~ 2026-11-16');

  await edited.getByRole('button', { name: `둘째주 ${name} 삭제` }).click();
  await dialog.getByRole('button', { name: '삭제' }).click();
  await expect(dialog.getByRole('alert')).toContainText('할 일 1개');
  await dialog.getByRole('button', { name: '취소' }).click();
  await expect(edited).toBeVisible();

  await page.request.delete(`/api/tasks/${task.id}`);
  await page.reload();
  await edited.getByRole('button', { name: `둘째주 ${name} 삭제` }).click();
  await dialog.getByRole('button', { name: '삭제' }).click();
  await expect(goalCard.getByTestId('goal-week')).toHaveCount(0);
  await expect(goalCard.getByText('주간 계획이 없습니다.')).toBeVisible();
});

test('목표 화면은 목표마다 자기 주간 계획만 보여 준다', async ({ page }) => {
  const name = unique();
  async function post(url: string, data: unknown) {
    return (await page.request.post(url, { data })).json();
  }
  const first = await post('/api/goals', { title: `가목표 ${name}`, year: 2026 });
  const second = await post('/api/goals', { title: `나목표 ${name}`, year: 2026 });
  const range = { startDate: '2026-11-02', endDate: '2026-11-08' };
  await post('/api/weeks', { goalId: first.id, title: `가주간 ${name}`, ...range });
  await post('/api/weeks', { goalId: second.id, title: `나주간 ${name}`, ...range });

  await page.goto('/goals');
  function cardOf(goal: { title: string }) {
    return page.getByTestId('goal-card').filter({ hasText: goal.title });
  }
  await expect(cardOf(first).getByTestId('goal-week')).toHaveCount(1);
  await expect(cardOf(first)).toContainText(`가주간 ${name}`);
  await expect(cardOf(first)).not.toContainText(`나주간 ${name}`);
  await expect(cardOf(second)).toContainText(`나주간 ${name}`);
});

test('Schedule 화면에서 월간 계획을 추가·수정·삭제하고 기간 안의 할 일로 진행률을 계산한다', async ({
  page,
}) => {
  const name = unique();
  const { goal, tasks } = await seed(page, [2, 3]);
  await page.request.patch(`/api/tasks/${tasks[0].id}`, { data: { status: 'done' } });
  await page.goto('/goals');
  const goalCard = page.getByTestId('goal-card').filter({ hasText: goal.title });
  const section = goalCard.getByTestId('month-section');
  const dialog = page.getByRole('dialog');
  await expect(section.getByText('월간 계획이 없습니다.')).toBeVisible();

  await section.getByRole('button', { name: '월간 계획 추가' }).click();
  await dialog.getByLabel('제목').fill(`잘못된달 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-11-30');
  await dialog.getByLabel('종료일').fill('2026-11-01');
  await dialog.getByRole('button', { name: '저장' }).click();
  await expect(dialog.getByRole('alert')).toContainText('시작일은 종료일보다');
  await dialog.getByRole('button', { name: '취소' }).click();
  await expect(section.getByTestId('goal-month')).toHaveCount(0);

  await section.getByRole('button', { name: '월간 계획 추가' }).click();
  await dialog.getByLabel('제목').fill(`11월 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-11-01');
  await dialog.getByLabel('종료일').fill('2026-11-30');
  await dialog.getByRole('button', { name: '저장' }).click();
  const added = section.getByTestId('goal-month').filter({ hasText: `11월 ${name}` });
  await expect(added).toContainText('2026-11-01 ~ 2026-11-30');
  await expect(added).toContainText('할 일 2개');
  await expect(added.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
  await expect(goalCard).toContainText('월간 계획 1개');

  await added.getByRole('button', { name: `11월 ${name} 수정` }).click();
  await dialog.getByLabel('제목').fill(`수정한달 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-12-01');
  await dialog.getByLabel('종료일').fill('2026-12-31');
  await dialog.getByRole('button', { name: '저장' }).click();
  const edited = section.getByTestId('goal-month').filter({ hasText: `수정한달 ${name}` });
  await expect(edited).toContainText('2026-12-01 ~ 2026-12-31');
  await expect(edited).toContainText('할 일 0개');
  await expect(edited.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  await page.reload();
  await expect(edited).toContainText('2026-12-01 ~ 2026-12-31');

  await goalCard.getByRole('button', { name: '삭제', exact: true }).click();
  await dialog.getByRole('button', { name: '삭제' }).click();
  await expect(dialog.getByRole('alert')).toContainText('월간 계획 1개');
  await dialog.getByRole('button', { name: '취소' }).click();

  await edited.getByRole('button', { name: `수정한달 ${name} 삭제` }).click();
  await dialog.getByRole('button', { name: '삭제' }).click();
  await expect(section.getByTestId('goal-month')).toHaveCount(0);
  await expect(section.getByText('월간 계획이 없습니다.')).toBeVisible();
});

test('Schedule 상세에서도 월간 계획을 추가한다', async ({ page }) => {
  const name = unique();
  const { goal } = await seed(page);
  await page.goto(`/goals/${goal.id}`);
  await page.getByRole('button', { name: '월간 계획 추가' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('제목').fill(`상세달 ${name}`);
  await dialog.getByLabel('시작일').fill('2026-11-01');
  await dialog.getByLabel('종료일').fill('2026-11-30');
  await dialog.getByRole('button', { name: '저장' }).click();
  const added = page.getByTestId('goal-month').filter({ hasText: `상세달 ${name}` });
  await expect(added).toContainText('할 일 2개');
  await expect(added.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
});

test('할 일 관리 홈의 새 할 일 폼으로 모든 항목을 입력해 할 일을 만든다', async ({ page }) => {
  const name = unique();
  const { week } = await seed(page, [2, 3]);
  await page.clock.setFixedTime(new Date('2026-11-03T12:00:00'));
  await page.goto('/');
  await page.getByRole('button', { name: '새 할 일' }).click();
  const dialog = page.getByRole('dialog');

  await dialog.getByLabel('제목').fill(`홈할일 ${name}`);
  await dialog.getByLabel('설명').fill('자세한 메모');
  await dialog.getByLabel('우선순위').selectOption('high');
  await dialog.getByLabel('상태').selectOption('done');
  await dialog.getByLabel('가중치').selectOption('3');
  await expect(dialog.getByLabel('마감일')).toHaveValue('2026-11-03');
  await dialog
    .getByLabel('주간 계획')
    .selectOption({ label: `${week.title} (2026-11-02 ~ 2026-11-08)` });
  await expect(dialog.getByTestId('week-impact')).toContainText('0% → 38%');
  await dialog.getByRole('button', { name: '저장' }).click();

  await expect(page.getByRole('status')).toContainText('할 일을 추가했습니다.');
  const row = page.getByTestId('today-task').filter({ hasText: `홈할일 ${name}` });
  await expect(row).toContainText('높음');
  await expect(row).toContainText('완료');

  const response = await page.request.get(`/api/tasks?weekId=${week.id}`);
  const saved: { title: string }[] = await response.json();
  expect(saved.find((task) => task.title === `홈할일 ${name}`)).toMatchObject({
    description: '자세한 메모',
    priority: 'high',
    status: 'done',
    weight: 3,
    date: '2026-11-03',
    weekId: week.id,
  });
});

test('새 할 일 폼에서 마감일과 주간 계획이 서로 연동된다', async ({ page }) => {
  const { goal, week } = await seed(page);
  const created = await page.request.post('/api/weeks', {
    data: {
      goalId: goal.id,
      title: `다음주 ${unique()}`,
      startDate: '2026-11-09',
      endDate: '2026-11-15',
    },
  });
  const nextWeek = await created.json();
  await page.clock.setFixedTime(new Date('2026-11-03T12:00:00'));
  await page.goto('/');
  await page.getByRole('button', { name: '새 할 일' }).click();
  const dialog = page.getByRole('dialog');

  await dialog.getByLabel('주간 계획').selectOption(week.id);
  await dialog.getByLabel('마감일').fill('2026-11-10');
  await expect(dialog.getByLabel('주간 계획')).toHaveValue(nextWeek.id);

  await dialog.getByLabel('주간 계획').selectOption(week.id);
  await expect(dialog.getByLabel('마감일')).toHaveValue('2026-11-08');

  await dialog.getByLabel('마감일').fill('2027-03-01');
  await expect(dialog.getByText('기간(2026-11-02 ~ 2026-11-08) 밖입니다')).toBeVisible();
});

test('주간 계획이 없으면 새 할 일 폼이 안내만 보여 주고 저장할 수 없다', async ({ page }) => {
  await page.route('**/api/weeks', (route) => route.fulfill({ json: [] }));
  await page.goto('/');
  await page.getByRole('button', { name: '새 할 일' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('연결할 주간 계획이 없습니다.');
  await expect(dialog.getByRole('button', { name: '저장' })).toBeDisabled();
});

test('보드에서 할 일을 수정하면 우선순위·설명·상태가 카드에 반영된다', async ({ page }) => {
  const { week } = await seed(page);
  await page.goto(`/weeks/${week.id}`);
  await card(page, '일 1').getByRole('button', { name: '수정' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('우선순위').selectOption('high');
  await dialog.getByLabel('설명').fill('꼭 끝낼 것');
  await dialog.getByLabel('상태').selectOption('doing');
  await dialog.getByRole('button', { name: '저장' }).click();

  await expect(column(page, 'doing')).toContainText('일 1');
  await expect(card(page, '일 1')).toContainText('높음');
  await expect(card(page, '일 1')).toContainText('꼭 끝낼 것');
  await expect(card(page, '일 2')).toContainText('보통');
});
