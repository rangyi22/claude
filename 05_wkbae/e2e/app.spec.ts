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
  await page.goto('/');
  await page.getByRole('button', { name: '새 목표' }).click();
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

  await page.goto('/');
  const row = page.getByTestId('goal-card').filter({ hasText: goal.title });
  await row.getByRole('button', { name: '삭제' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '삭제' }).click();
  await expect(alert(page)).toContainText('주간 계획 1개');
  await page.getByRole('button', { name: '취소' }).click();

  await row.getByRole('button', { name: '수정' }).click();
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
  await page.getByLabel('날짜').fill('2026-12-25');
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
