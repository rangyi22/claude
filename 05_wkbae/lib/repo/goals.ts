import { ObjectId } from 'mongodb';
import { collections, USER_ID, type GoalDoc } from '../db';
import { AppError, notFound } from '../errors';
import type { Goal, GoalDetail } from '../types';
import { goalCreateSchema, goalUpdateSchema } from '../validation';
import { parseId } from './ids';
import { progressForGoals } from './progress';
import { listWeeks } from './weeks';

function toGoal(doc: GoalDoc, progress: number, weekCount: number): Goal {
  return { id: doc._id.toHexString(), title: doc.title, year: doc.year, progress, weekCount };
}

export async function listGoals(): Promise<Goal[]> {
  const { goals, weeks } = await collections();
  const docs = await goals.find({ userId: USER_ID }).sort({ year: -1, createdAt: 1 }).toArray();
  const progress = await progressForGoals(docs.map((doc) => doc._id));
  const counts = await weeks
    .aggregate<{ _id: ObjectId; count: number }>([
      { $match: { userId: USER_ID } },
      { $group: { _id: '$goalId', count: { $sum: 1 } } },
    ])
    .toArray();
  const countByGoal = new Map(counts.map((row) => [row._id.toHexString(), row.count]));

  return docs.map((doc) => {
    const key = doc._id.toHexString();
    return toGoal(doc, progress.get(key) ?? 0, countByGoal.get(key) ?? 0);
  });
}

export async function getGoal(id: string): Promise<GoalDetail> {
  const { goals } = await collections();
  const _id = parseId(id, '목표');
  const doc = await goals.findOne({ _id, userId: USER_ID });
  if (!doc) throw notFound('목표');
  const weeks = await listWeeks(id);
  const progress = await progressForGoals([_id]);
  return { ...toGoal(doc, progress.get(id) ?? 0, weeks.length), weeks };
}

export async function createGoal(input: unknown): Promise<Goal> {
  const { goals } = await collections();
  const data = goalCreateSchema.parse(input);
  const doc: GoalDoc = { _id: new ObjectId(), userId: USER_ID, ...data, createdAt: new Date() };
  await goals.insertOne(doc);
  return toGoal(doc, 0, 0);
}

export async function updateGoal(id: string, input: unknown): Promise<Goal> {
  const { goals } = await collections();
  const _id = parseId(id, '목표');
  const data = goalUpdateSchema.parse(input);
  const doc = await goals.findOneAndUpdate(
    { _id, userId: USER_ID },
    { $set: data },
    { returnDocument: 'after' },
  );
  if (!doc) throw notFound('목표');
  const { weekCount, progress } = await getGoal(id);
  return toGoal(doc, progress, weekCount);
}

export async function deleteGoal(id: string): Promise<void> {
  const { goals, weeks } = await collections();
  const _id = parseId(id, '목표');
  if (!(await goals.findOne({ _id, userId: USER_ID }))) throw notFound('목표');

  const childCount = await weeks.countDocuments({ goalId: _id, userId: USER_ID });
  if (childCount > 0) {
    throw new AppError(
      409,
      `연결된 주간 계획 ${childCount}개가 있어 삭제할 수 없습니다. 주간 계획을 먼저 삭제하세요.`,
      { childCount },
    );
  }
  await goals.deleteOne({ _id, userId: USER_ID });
}
