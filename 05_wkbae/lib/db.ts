import { Db, MongoClient, type ObjectId } from 'mongodb';
import type { TaskPriority, TaskStatus } from './types';

export const USER_ID = 'local';

export interface GoalDoc {
  _id: ObjectId;
  userId: string;
  title: string;
  year: number;
  createdAt: Date;
}

export interface WeekDoc {
  _id: ObjectId;
  userId: string;
  goalId: ObjectId;
  title: string;
  startDate: string;
  endDate: string;
  createdAt: Date;
}

export interface MonthDoc {
  _id: ObjectId;
  userId: string;
  goalId: ObjectId;
  title: string;
  startDate: string;
  endDate: string;
  createdAt: Date;
}

export interface TaskDoc {
  _id: ObjectId;
  userId: string;
  weekId: ObjectId;
  title: string;
  date: string;
  weight: number;
  status: TaskStatus;
  order: number;
  /** 설명과 우선순위는 나중에 추가된 필드라, 이전에 만든 할 일에는 없을 수 있다. */
  description?: string;
  priority?: TaskPriority;
  createdAt: Date;
  updatedAt: Date;
}

interface Connection {
  client: MongoClient;
  db: Promise<Db>;
}

// 개발 서버 핫리로드 때 모듈이 다시 평가되어도 연결을 하나만 쓰도록 globalThis에 보관한다.
const cache = globalThis as typeof globalThis & { __todoMongo?: Connection };

async function prepare(client: MongoClient): Promise<Db> {
  await client.connect();
  const db = client.db(process.env.MONGODB_DB ?? 'todo_app');
  await Promise.all([
    db.collection('weeks').createIndex({ goalId: 1 }),
    db.collection('months').createIndex({ goalId: 1 }),
    db.collection('tasks').createIndex({ weekId: 1 }),
    db.collection('tasks').createIndex({ weekId: 1, status: 1, order: 1 }),
    db.collection('tasks').createIndex({ date: 1 }),
  ]);
  return db;
}

export function getDb(): Promise<Db> {
  if (!cache.__todoMongo) {
    const uri = process.env.MONGODB_URI;
    if (!uri) throw new Error('MONGODB_URI가 설정되지 않았습니다.');
    const client = new MongoClient(uri);
    cache.__todoMongo = { client, db: prepare(client) };
    cache.__todoMongo.db.catch(() => {
      cache.__todoMongo = undefined;
    });
  }
  return cache.__todoMongo.db;
}

export async function closeDb(): Promise<void> {
  await cache.__todoMongo?.client.close();
  cache.__todoMongo = undefined;
}

export async function collections() {
  const db = await getDb();
  return {
    goals: db.collection<GoalDoc>('goals'),
    weeks: db.collection<WeekDoc>('weeks'),
    months: db.collection<MonthDoc>('months'),
    tasks: db.collection<TaskDoc>('tasks'),
  };
}
