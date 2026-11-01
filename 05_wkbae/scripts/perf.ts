/* eslint-disable no-console -- 측정 결과를 터미널에 출력하는 스크립트다. */
import { chromium } from '@playwright/test';
import { MongoClient, ObjectId } from 'mongodb';
import { startTestServer, waitForServer } from './testServer';

const PORT = 3200;
const BASE = `http://localhost:${PORT}`;
const TASK_COUNT = 1_000;
const SAMPLES = 50;

async function seed(uri: string) {
  const client = await MongoClient.connect(uri);
  const db = client.db('todo_test');
  const goalId = new ObjectId();
  const weekId = new ObjectId();
  const now = new Date();
  await db.collection('goals').insertOne({
    _id: goalId,
    userId: 'local',
    title: '성능',
    year: 2026,
    createdAt: now,
  });
  await db.collection('weeks').insertOne({
    _id: weekId,
    userId: 'local',
    goalId,
    title: '성능 주간',
    startDate: '2026-11-02',
    endDate: '2026-11-08',
    createdAt: now,
  });
  await db.collection('tasks').insertMany(
    Array.from({ length: TASK_COUNT }, (_, index) => ({
      userId: 'local',
      weekId,
      title: `할 일 ${index}`,
      date: '2026-11-03',
      weight: (index % 5) + 1,
      status: 'todo',
      order: index,
      createdAt: now,
      updatedAt: now,
    })),
  );
  const tasks = await db.collection('tasks').find().limit(SAMPLES).toArray();
  await client.close();
  return { weekId: weekId.toHexString(), taskIds: tasks.map((task) => task._id.toHexString()) };
}

function p95(samples: number[]): number {
  const sorted = [...samples].sort((a, b) => a - b);
  return Math.round(sorted[Math.ceil(sorted.length * 0.95) - 1]);
}

async function timedFetch(url: string, init?: RequestInit): Promise<number> {
  const start = performance.now();
  const response = await fetch(url, init);
  await response.text();
  const elapsed = performance.now() - start;
  if (!response.ok) throw new Error(`${url} 응답 ${response.status}`);
  return elapsed;
}

async function timed(work: () => Promise<unknown>): Promise<number> {
  const start = performance.now();
  await work();
  return performance.now() - start;
}

async function main() {
  const server = await startTestServer(PORT);
  try {
    await waitForServer(BASE);
    const { weekId, taskIds } = await seed(server.uri);

    const patchTimes: number[] = [];
    for (const id of taskIds) {
      patchTimes.push(
        await timedFetch(`${BASE}/api/tasks/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'doing' }),
        }),
      );
    }
    const getTimes: number[] = [];
    for (let sample = 0; sample < SAMPLES; sample += 1) {
      getTimes.push(await timedFetch(`${BASE}/api/weeks/${weekId}`));
    }

    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    const boardLoad = await timed(async () => {
      await page.goto(`${BASE}/weeks/${weekId}`);
      await page.getByTestId('task-card').first().waitFor();
    });

    const first = page.getByTestId('column-todo').getByTestId('task-card').first();
    const title = (await first.locator('p').textContent()) ?? '';
    const source = (await first.boundingBox())!;
    const target = (await page.getByTestId('column-done').boundingBox())!;
    await page.mouse.move(source.x + source.width / 2, source.y + 12);
    await page.mouse.down();
    await page.mouse.move(source.x + source.width / 2 + 10, source.y + 12, { steps: 3 });
    await page.mouse.move(target.x + target.width / 2, target.y + 200, { steps: 5 });
    const dragResponse = await timed(async () => {
      await page.mouse.up();
      await page.getByTestId('column-done').getByText(title, { exact: true }).waitFor();
    });
    await browser.close();

    const result = {
      taskCount: TASK_COUNT,
      patchP95Ms: p95(patchTimes),
      weekGetP95Ms: p95(getTimes),
      boardLoadMs: Math.round(boardLoad),
      dragResponseMs: Math.round(dragResponse),
    };
    console.log(JSON.stringify(result, null, 2));
    const passed =
      result.patchP95Ms <= 300 &&
      result.weekGetP95Ms <= 300 &&
      result.boardLoadMs <= 1000 &&
      result.dragResponseMs <= 100;
    if (!passed) process.exitCode = 1;
  } finally {
    await server.stop();
  }
}

void main();
