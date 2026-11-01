import type { ObjectId } from 'mongodb';
import { collections, USER_ID } from '../db';
import { calcProgress } from '../progress';
import type { ProgressSnapshot, TaskStatus } from '../types';

interface WeightedTask {
  weekId: ObjectId;
  weight: number;
  status: TaskStatus;
}

export async function loadWeightedTasks(weekIds: ObjectId[]): Promise<WeightedTask[]> {
  if (weekIds.length === 0) return [];
  const { tasks } = await collections();
  return tasks
    .find(
      { userId: USER_ID, weekId: { $in: weekIds } },
      { projection: { _id: 0, weekId: 1, weight: 1, status: 1 } },
    )
    .toArray();
}

export function groupByWeek(tasks: WeightedTask[]): Map<string, WeightedTask[]> {
  const groups = new Map<string, WeightedTask[]>();
  for (const task of tasks) {
    const key = task.weekId.toHexString();
    const group = groups.get(key);
    if (group) group.push(task);
    else groups.set(key, [task]);
  }
  return groups;
}

/** 주간 가중치가 할 일 가중치 합이므로 목표 진행률은 소속 할 일 전체로 계산한 값과 같다. */
export async function progressForGoals(goalIds: ObjectId[]): Promise<Map<string, number>> {
  const { weeks } = await collections();
  const weekDocs = await weeks
    .find({ userId: USER_ID, goalId: { $in: goalIds } }, { projection: { goalId: 1 } })
    .toArray();
  const tasks = groupByWeek(await loadWeightedTasks(weekDocs.map((week) => week._id)));

  const byGoal = new Map<string, WeightedTask[]>();
  for (const week of weekDocs) {
    const key = week.goalId.toHexString();
    const goalTasks = byGoal.get(key) ?? [];
    goalTasks.push(...(tasks.get(week._id.toHexString()) ?? []));
    byGoal.set(key, goalTasks);
  }
  return new Map(
    goalIds.map((id) => [id.toHexString(), calcProgress(byGoal.get(id.toHexString()) ?? [])]),
  );
}

export async function progressSnapshot(weekIds: ObjectId[]): Promise<ProgressSnapshot> {
  const { weeks } = await collections();
  const weekDocs = await weeks
    .find({ userId: USER_ID, _id: { $in: weekIds } }, { projection: { goalId: 1 } })
    .toArray();
  const tasks = groupByWeek(await loadWeightedTasks(weekDocs.map((week) => week._id)));
  const goalProgress = await progressForGoals(weekDocs.map((week) => week.goalId));

  return {
    weeks: Object.fromEntries(
      weekDocs.map((week) => {
        const key = week._id.toHexString();
        return [key, calcProgress(tasks.get(key) ?? [])];
      }),
    ),
    goals: Object.fromEntries(goalProgress),
  };
}
