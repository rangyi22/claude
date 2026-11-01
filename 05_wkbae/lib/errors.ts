export class AppError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
  }
}

export function notFound(label: string): AppError {
  return new AppError(404, `${label}을(를) 찾을 수 없습니다.`);
}
