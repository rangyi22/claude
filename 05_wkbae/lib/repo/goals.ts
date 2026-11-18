import { ObjectId } from 'mongodb';
import { collections, USER_ID, type GoalDoc } from '../db';
import { AppError, notFound } from '../errors';
import type { Goal, GoalDetail } from '../types';
import { goalCreateSchema, goalUpdateSchema } from '../validation';
import { parseId } from './ids';
import { listMonths } from './months';
import { progressForGoals } from './progress';
import { listWeeks } from './weeks';

function toGoal(doc: GoalDoc, progress: number, weekCount: number, monthCount: number): Goal {
  return {
    id: doc._id.toHexString(),
    title: doc.title,
    year: doc.year,
    progress,
    weekCount,
    monthCount,
  };
}

async function countByGoal(collection: 'weeks' | 'months'): Promise<Map<string, number>> {
  const db = await collections();
  const counts = await db[collection]
    .aggregate<{ _id: ObjectId; count: number }>([
      { $match: { userId: USER_ID } },
      { $group: { _id: '$goalId', count: { $sum: 1 } } },
    ])
    .toArray();
  return new Map(counts.map((row) => [row._id.toHexString(), row.count]));
}

export async function listGoals(): Promise<Goal[]> {
  const { goals } = await collections();
  const docs = await goals.find({ userId: USER_ID }).sort({ year: -1, createdAt: 1 }).toArray();
  const progress = await progressForGoals(docs.map((doc) => doc._id));
  const [weekCounts, monthCounts] = await Promise.all([
    countByGoal('weeks'),
    countByGoal('months'),
  ]);

  return docs.map((doc) => {
    const key = doc._id.toHexString();
    return toGoal(doc, progress.get(key) ?? 0, weekCounts.get(key) ?? 0, monthCounts.get(key) ?? 0);
  });
}

export async function getGoal(id: string): Promise<GoalDetail> {
  const { goals } = await collections();
  const _id = parseId(id, 'Schedule');
  const doc = await goals.findOne({ _id, userId: USER_ID });
  if (!doc) throw notFound('Schedule');
  const [weeks, months] = await Promise.all([listWeeks(id), listMonths(id)]);
  const progress = await progressForGoals([_id]);
  return { ...toGoal(doc, progress.get(id) ?? 0, weeks.length, months.length), weeks, months };
}

export async function createGoal(input: unknown): Promise<Goal> {
  const { goals } = await collections();
  const data = goalCreateSchema.parse(input);
  const doc: GoalDoc = { _id: new ObjectId(), userId: USER_ID, ...data, createdAt: new Date() };
  await goals.insertOne(doc);
  return toGoal(doc, 0, 0, 0);
}

export async function updateGoal(id: string, input: unknown): Promise<Goal> {
  const { goals } = await collections();
  const _id = parseId(id, 'Schedule');
  const data = goalUpdateSchema.parse(input);
  const doc = await goals.findOneAndUpdate(
    { _id, userId: USER_ID },
    { $set: data },
    { returnDocument: 'after' },
  );
  if (!doc) throw notFound('Schedule');
  const { weekCount, monthCount, progress } = await getGoal(id);
  return toGoal(doc, progress, weekCount, monthCount);
}

export async function deleteGoal(id: string): Promise<void> {
  const { goals, weeks, months } = await collections();
  const _id = parseId(id, 'Schedule');
  if (!(await goals.findOne({ _id, userId: USER_ID }))) throw notFound('Schedule');

  const [weekCount, monthCount] = await Promise.all([
    weeks.countDocuments({ goalId: _id, userId: USER_ID }),
    months.countDocuments({ goalId: _id, userId: USER_ID }),
  ]);
  const childCount = weekCount + monthCount;
  if (childCount > 0) {
    const parts = [
      weekCount > 0 && `주간 계획 ${weekCount}개`,
      monthCount > 0 && `월간 계획 ${monthCount}개`,
    ]
      .filter(Boolean)
      .join(', ');
    throw new AppError(
      409,
      `연결된 ${parts}가 있어 삭제할 수 없습니다. 하위 계획을 먼저 삭제하세요.`,
      { childCount, weekCount, monthCount },
    );
  }
  await goals.deleteOne({ _id, userId: USER_ID });
}
