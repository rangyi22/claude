import { z } from 'zod';
import { isValidDate } from './dates';
import { TASK_PRIORITIES, TASK_STATUSES } from './types';

const title = z.string('제목을 입력하세요.').trim().min(1, '제목을 입력하세요.').max(200);
const DATE_MESSAGE = '날짜는 YYYY-MM-DD 형식이어야 합니다.';
const date = z.string(DATE_MESSAGE).refine(isValidDate, DATE_MESSAGE);
const weight = z
  .number('가중치는 1~5 정수여야 합니다.')
  .int('가중치는 1~5 정수여야 합니다.')
  .min(1, '가중치는 1~5 정수여야 합니다.')
  .max(5, '가중치는 1~5 정수여야 합니다.');
const description = z
  .string('설명이 올바르지 않습니다.')
  .trim()
  .max(2000, '설명은 2000자 이내로 입력하세요.');
const priority = z.enum(TASK_PRIORITIES, '우선순위가 올바르지 않습니다.');
const status = z.enum(TASK_STATUSES, '상태가 올바르지 않습니다.');
const year = z.number('연도를 입력하세요.').int().min(1970).max(9999);

const GOAL_REQUIRED = '주간 계획은 Schedule에 연결해야 합니다.';
const MONTH_REQUIRED = '월간 계획은 Schedule에 연결해야 합니다.';
const WEEK_REQUIRED = '할 일은 주간 계획에 연결해야 합니다.';

const startBeforeEnd = {
  error: '시작일은 종료일보다 늦을 수 없습니다.',
  path: ['endDate'],
};

export const dateQuerySchema = date.optional();

export const goalCreateSchema = z.strictObject({ title, year });
export const goalUpdateSchema = z.strictObject({ title: title.optional(), year: year.optional() });

export const weekCreateSchema = z
  .strictObject({
    goalId: z.string(GOAL_REQUIRED).min(1, GOAL_REQUIRED),
    title,
    startDate: date,
    endDate: date,
  })
  .refine((week) => week.startDate <= week.endDate, startBeforeEnd);

export const weekUpdateSchema = z.strictObject({
  title: title.optional(),
  startDate: date.optional(),
  endDate: date.optional(),
});

export const rangeSchema = z
  .object({ startDate: date, endDate: date })
  .refine((week) => week.startDate <= week.endDate, startBeforeEnd);

export const monthCreateSchema = z
  .strictObject({
    goalId: z.string(MONTH_REQUIRED).min(1, MONTH_REQUIRED),
    title,
    startDate: date,
    endDate: date,
  })
  .refine((month) => month.startDate <= month.endDate, startBeforeEnd);

export const monthUpdateSchema = z.strictObject({
  title: title.optional(),
  startDate: date.optional(),
  endDate: date.optional(),
});

export const taskCreateSchema = z.strictObject({
  weekId: z.string(WEEK_REQUIRED).min(1, WEEK_REQUIRED),
  title,
  date,
  weight: weight.default(1),
  description: description.default(''),
  priority: priority.default('medium'),
  status: status.default('todo'),
});

export const taskUpdateSchema = z.strictObject({
  weekId: z.string(WEEK_REQUIRED).min(1, WEEK_REQUIRED).optional(),
  title: title.optional(),
  date: date.optional(),
  weight: weight.optional(),
  description: description.optional(),
  priority: priority.optional(),
  status: status.optional(),
  order: z.number('순서가 올바르지 않습니다.').finite().optional(),
});

export const carryOverSchema = z.strictObject({
  createIfMissing: z.boolean().default(false),
});
