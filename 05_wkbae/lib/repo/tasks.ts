import { ObjectId, type Filter } from 'mongodb';
import { collections, USER_ID, type TaskDoc, type WeekDoc } from '../db';
import { AppError, notFound } from '../errors';
import type { Task, TaskMutationResult, TaskStatus } from '../types';
import { taskCreateSchema, taskUpdateSchema } from '../validation';
import { missingParent, parseId, parseParentId } from './ids';
import { progressSnapshot } from './progress';

export function toTask(doc: TaskDoc): Task {
  return {
    id: doc._id.toHexString(),
    weekId: doc.weekId.toHexString(),
    title: doc.title,
    date: doc.date,
    weight: doc.weight,
    status: doc.status,
    order: doc.order,
  };
}

export interface TaskFilter {
  weekId?: string;
  from?: string;
  to?: string;
}

export async function listTasks({ weekId, from, to }: TaskFilter = {}): Promise<Task[]> {
  const { tasks } = await collections();
  const filter: Filter<TaskDoc> = { userId: USER_ID };
  if (weekId) filter.weekId = parseId(weekId, '주간 계획');
  if (from || to) {
    filter.date = { ...(from ? { $gte: from } : {}), ...(to ? { $lte: to } : {}) };
  }
  const docs = await tasks.find(filter).sort({ date: 1, order: 1 }).toArray();
  return docs.map(toTask);
}

async function findParentWeek(weekId: ObjectId): Promise<WeekDoc> {
  const { weeks } = await collections();
  const week = await weeks.findOne({ _id: weekId, userId: USER_ID });
  if (!week) throw missingParent('주간 계획');
  return week;
}

function assertInRange(date: string, week: WeekDoc): void {
  if (date < week.startDate || date > week.endDate) {
    throw new AppError(
      400,
      `할 일 날짜는 주간 계획 기간(${week.startDate} ~ ${week.endDate}) 안이어야 합니다.`,
    );
  }
}

export async function nextOrder(weekId: ObjectId, status: TaskStatus): Promise<number> {
  const { tasks } = await collections();
  const last = await tasks.findOne(
    { userId: USER_ID, weekId, status },
    { sort: { order: -1 }, projection: { order: 1 } },
  );
  return (last?.order ?? 0) + 1;
}

export async function createTask(input: unknown): Promise<TaskMutationResult> {
  const { tasks } = await collections();
  const { weekId, ...data } = taskCreateSchema.parse(input);
  const parent = parseParentId(weekId, '주간 계획');
  assertInRange(data.date, await findParentWeek(parent));

  const now = new Date();
  const doc: TaskDoc = {
    _id: new ObjectId(),
    userId: USER_ID,
    weekId: parent,
    ...data,
    status: 'todo',
    order: await nextOrder(parent, 'todo'),
    createdAt: now,
    updatedAt: now,
  };
  await tasks.insertOne(doc);
  return { task: toTask(doc), progress: await progressSnapshot([parent]) };
}

export async function updateTask(id: string, input: unknown): Promise<TaskMutationResult> {
  const { tasks } = await collections();
  const _id = parseId(id, '할 일');
  const current = await tasks.findOne({ _id, userId: USER_ID });
  if (!current) throw notFound('할 일');

  const { weekId, ...data } = taskUpdateSchema.parse(input);
  const nextWeekId = weekId ? parseParentId(weekId, '주간 계획') : current.weekId;
  const nextDate = data.date ?? current.date;
  if (weekId || data.date) assertInRange(nextDate, await findParentWeek(nextWeekId));

  const nextStatus = data.status ?? current.status;
  const movedColumn = nextStatus !== current.status || !nextWeekId.equals(current.weekId);
  const order =
    data.order ?? (movedColumn ? await nextOrder(nextWeekId, nextStatus) : current.order);

  const doc = await tasks.findOneAndUpdate(
    { _id, userId: USER_ID },
    { $set: { ...data, weekId: nextWeekId, order, updatedAt: new Date() } },
    { returnDocument: 'after' },
  );
  if (!doc) throw notFound('할 일');
  return {
    task: toTask(doc),
    progress: await progressSnapshot([current.weekId, nextWeekId]),
  };
}

export async function deleteTask(id: string): Promise<TaskMutationResult['progress']> {
  const { tasks } = await collections();
  const doc = await tasks.findOneAndDelete({ _id: parseId(id, '할 일'), userId: USER_ID });
  if (!doc) throw notFound('할 일');
  return progressSnapshot([doc.weekId]);
}
