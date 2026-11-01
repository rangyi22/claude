import { ObjectId } from 'mongodb';
import { AppError, notFound } from '../errors';

export function parseId(id: string, label: string): ObjectId {
  if (!ObjectId.isValid(id)) throw notFound(label);
  return new ObjectId(id);
}

export function missingParent(label: string): AppError {
  return new AppError(400, `연결할 ${label}을(를) 찾을 수 없습니다.`);
}

export function parseParentId(id: string, label: string): ObjectId {
  if (!ObjectId.isValid(id)) throw missingParent(label);
  return new ObjectId(id);
}
