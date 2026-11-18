import { ObjectId } from 'mongodb';
import { collections, USER_ID, type MonthDoc } from '../db';
import { notFound } from '../errors';
import { calcProgress } from '../progress';
import type { Month } from '../types';
import { monthCreateSchema, monthUpdateSchema, rangeSchema } from '../validation';
import { missingParent, parseId, parseParentId } from './ids';

function toMonth(doc: MonthDoc, progress: number, taskCount: number): Month {
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

/** 월간 계획은 주간 계획과 따로 존재하므로, 같은 Schedule의 할 일 중 기간 안에 날짜가 든 것으로 계산한다. */
async function withProgress(docs: MonthDoc[]): Promise<Month[]> {
  if (docs.length === 0) return [];
  const { weeks, tasks } = await collections();
  const goalIds = [...new Set(docs.map((doc) => doc.goalId.toHexString()))].map(
    (id) => new ObjectId(id),
  );
  const weekDocs = await weeks
    .find({ userId: USER_ID, goalId: { $in: goalIds } }, { projection: { goalId: 1 } })
    .toArray();
  const goalOfWeek = new Map(
    weekDocs.map((week) => [week._id.toHexString(), week.goalId.toHexString()]),
  );

  const from = docs.reduce(
    (min, doc) => (doc.startDate < min ? doc.startDate : min),
    docs[0].startDate,
  );
  const to = docs.reduce((max, doc) => (doc.endDate > max ? doc.endDate : max), docs[0].endDate);
  const rows =
    weekDocs.length === 0
      ? []
      : await tasks
          .find(
            {
              userId: USER_ID,
              weekId: { $in: weekDocs.map((week) => week._id) },
              date: { $gte: from, $lte: to },
            },
            { projection: { weekId: 1, date: 1, weight: 1, status: 1 } },
          )
          .toArray();

  return docs.map((doc) => {
    const goal = doc.goalId.toHexString();
    const inRange = rows.filter(
      (task) =>
        goalOfWeek.get(task.weekId.toHexString()) === goal &&
        task.date >= doc.startDate &&
        task.date <= doc.endDate,
    );
    return toMonth(doc, calcProgress(inRange), inRange.length);
  });
}

export async function listMonths(goalId?: string): Promise<Month[]> {
  const { months } = await collections();
  const filter = goalId
    ? { userId: USER_ID, goalId: parseId(goalId, 'Schedule') }
    : { userId: USER_ID };
  return withProgress(await months.find(filter).sort({ startDate: 1 }).toArray());
}

async function findMonth(id: string): Promise<MonthDoc> {
  const { months } = await collections();
  const doc = await months.findOne({ _id: parseId(id, '월간 계획'), userId: USER_ID });
  if (!doc) throw notFound('월간 계획');
  return doc;
}

export async function createMonth(input: unknown): Promise<Month> {
  const { goals, months } = await collections();
  const { goalId, ...data } = monthCreateSchema.parse(input);
  const parent = parseParentId(goalId, 'Schedule');
  if (!(await goals.findOne({ _id: parent, userId: USER_ID }))) throw missingParent('Schedule');

  const doc: MonthDoc = {
    _id: new ObjectId(),
    userId: USER_ID,
    goalId: parent,
    ...data,
    createdAt: new Date(),
  };
  await months.insertOne(doc);
  const [month] = await withProgress([doc]);
  return month;
}

export async function updateMonth(id: string, input: unknown): Promise<Month> {
  const { months } = await collections();
  const current = await findMonth(id);
  const data = monthUpdateSchema.parse(input);
  rangeSchema.parse({
    startDate: data.startDate ?? current.startDate,
    endDate: data.endDate ?? current.endDate,
  });

  const doc = await months.findOneAndUpdate(
    { _id: current._id, userId: USER_ID },
    { $set: data },
    { returnDocument: 'after' },
  );
  if (!doc) throw notFound('월간 계획');
  const [month] = await withProgress([doc]);
  return month;
}

export async function deleteMonth(id: string): Promise<void> {
  const { months } = await collections();
  const { _id } = await findMonth(id);
  await months.deleteOne({ _id, userId: USER_ID });
}
