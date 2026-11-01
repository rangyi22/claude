import { ObjectId } from 'mongodb';
import { collections, USER_ID, type WeekDoc } from '../db';
import { addDays, clampDate, daysBetween } from '../dates';
import { AppError, notFound } from '../errors';
import { calcProgress } from '../progress';
import type { TaskStatus, Week, WeekDetail } from '../types';
import {
  carryOverSchema,
  weekCreateSchema,
  weekRangeSchema,
  weekUpdateSchema,
} from '../validation';
import { missingParent, parseId, parseParentId } from './ids';
import { groupByWeek, loadWeightedTasks, progressForGoals } from './progress';
import { listTasks, nextOrder } from './tasks';

function toWeek(doc: WeekDoc, progress: number, taskCount: number): Week {
  return {
    id: doc._id.toHexString(),
    goalId: doc.goalId.toHexString(),
    title: doc.title,
    startDate: doc.startDate,
    endDate: doc.endDate,
    progress,
    taskCount,
  };
}

async function withProgress(docs: WeekDoc[]): Promise<Week[]> {
  const tasks = groupByWeek(await loadWeightedTasks(docs.map((doc) => doc._id)));
  return docs.map((doc) => {
    const weekTasks = tasks.get(doc._id.toHexString()) ?? [];
    return toWeek(doc, calcProgress(weekTasks), weekTasks.length);
  });
}

export async function listWeeks(goalId?: string): Promise<Week[]> {
  const { weeks } = await collections();
  const filter = goalId
    ? { userId: USER_ID, goalId: parseId(goalId, '목표') }
    : { userId: USER_ID };
  return withProgress(await weeks.find(filter).sort({ startDate: 1 }).toArray());
}

async function findWeek(id: string): Promise<WeekDoc> {
  const { weeks } = await collections();
  const doc = await weeks.findOne({ _id: parseId(id, '주간 계획'), userId: USER_ID });
  if (!doc) throw notFound('주간 계획');
  return doc;
}

export async function getWeek(id: string): Promise<WeekDetail> {
  const { goals } = await collections();
  const doc = await findWeek(id);
  const [week] = await withProgress([doc]);
  const goal = await goals.findOne({ _id: doc.goalId, userId: USER_ID });
  const goalProgress = await progressForGoals([doc.goalId]);
  return {
    ...week,
    goalTitle: goal?.title ?? '',
    goalProgress: goalProgress.get(week.goalId) ?? 0,
    tasks: await listTasks({ weekId: id }),
  };
}

export async function createWeek(input: unknown): Promise<Week> {
  const { goals, weeks } = await collections();
  const { goalId, ...data } = weekCreateSchema.parse(input);
  const parent = parseParentId(goalId, '목표');
  if (!(await goals.findOne({ _id: parent, userId: USER_ID }))) {
    throw missingParent('목표');
  }
  const doc: WeekDoc = {
    _id: new ObjectId(),
    userId: USER_ID,
    goalId: parent,
    ...data,
    createdAt: new Date(),
  };
  await weeks.insertOne(doc);
  return toWeek(doc, 0, 0);
}

export async function updateWeek(id: string, input: unknown): Promise<Week> {
  const { tasks, weeks } = await collections();
  const current = await findWeek(id);
  const data = weekUpdateSchema.parse(input);
  const range = weekRangeSchema.parse({
    startDate: data.startDate ?? current.startDate,
    endDate: data.endDate ?? current.endDate,
  });

  const outside = await tasks.countDocuments({
    userId: USER_ID,
    weekId: current._id,
    $or: [{ date: { $lt: range.startDate } }, { date: { $gt: range.endDate } }],
  });
  if (outside > 0) {
    throw new AppError(
      409,
      `기간을 벗어나는 할 일 ${outside}개가 있어 저장할 수 없습니다. 할 일 날짜를 먼저 옮기세요.`,
      { outsideCount: outside },
    );
  }

  const doc = await weeks.findOneAndUpdate(
    { _id: current._id, userId: USER_ID },
    { $set: data },
    { returnDocument: 'after' },
  );
  if (!doc) throw notFound('주간 계획');
  const [week] = await withProgress([doc]);
  return week;
}

export async function deleteWeek(id: string): Promise<void> {
  const { tasks, weeks } = await collections();
  const { _id } = await findWeek(id);
  const childCount = await tasks.countDocuments({ weekId: _id, userId: USER_ID });
  if (childCount > 0) {
    throw new AppError(
      409,
      `연결된 할 일 ${childCount}개가 있어 삭제할 수 없습니다. 할 일을 옮기거나 먼저 삭제하세요.`,
      { childCount },
    );
  }
  await weeks.deleteOne({ _id, userId: USER_ID });
}

async function findNextWeek(current: WeekDoc): Promise<WeekDoc | null> {
  const { weeks } = await collections();
  return weeks.findOne(
    {
      userId: USER_ID,
      goalId: current.goalId,
      startDate: { $gt: current.endDate, $lte: addDays(current.endDate, 7) },
    },
    { sort: { startDate: 1 } },
  );
}

async function createFollowingWeek(current: WeekDoc): Promise<WeekDoc> {
  const { weeks } = await collections();
  const startDate = addDays(current.endDate, 1);
  const doc: WeekDoc = {
    _id: new ObjectId(),
    userId: USER_ID,
    goalId: current.goalId,
    title: `${startDate} 주간`,
    startDate,
    endDate: addDays(startDate, daysBetween(current.startDate, current.endDate)),
    createdAt: new Date(),
  };
  await weeks.insertOne(doc);
  return doc;
}

export interface CarryOverResult {
  weekId: string;
  movedCount: number;
}

export async function carryOver(id: string, input: unknown): Promise<CarryOverResult> {
  const { tasks } = await collections();
  const current = await findWeek(id);
  const { createIfMissing } = carryOverSchema.parse(input);

  const pending = await tasks
    .find({ userId: USER_ID, weekId: current._id, status: { $ne: 'done' } })
    .sort({ status: 1, order: 1 })
    .toArray();
  if (pending.length === 0) return { weekId: id, movedCount: 0 };

  let next = await findNextWeek(current);
  if (!next) {
    if (!createIfMissing) {
      throw new AppError(409, '다음 주 계획이 없습니다.', { nextWeekMissing: true });
    }
    next = await createFollowingWeek(current);
  }

  const orders = new Map<TaskStatus, number>();
  const updates = [];
  for (const task of pending) {
    const order = orders.get(task.status) ?? (await nextOrder(next._id, task.status));
    orders.set(task.status, order + 1);
    updates.push({
      updateOne: {
        filter: { _id: task._id, userId: USER_ID },
        update: {
          $set: {
            weekId: next._id,
            date: clampDate(addDays(task.date, 7), next.startDate, next.endDate),
            order,
            updatedAt: new Date(),
          },
        },
      },
    });
  }
  await tasks.bulkWrite(updates);
  return { weekId: next._id.toHexString(), movedCount: pending.length };
}
