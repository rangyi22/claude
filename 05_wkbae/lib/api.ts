export const REQUEST_TIMEOUT_MS = 5_000;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly body: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(0, '서버에 연결하지 못했습니다. 잠시 후 다시 시도하세요.');
  }

  const data: unknown = await response.json().catch(() => undefined);
  if (response.ok && data === undefined) {
    throw new ApiError(0, '서버 응답을 읽지 못했습니다. 잠시 후 다시 시도하세요.');
  }
  if (!response.ok) {
    const fields = (data ?? {}) as Record<string, unknown>;
    const message = typeof fields.error === 'string' ? fields.error : '요청을 처리하지 못했습니다.';
    throw new ApiError(response.status, message, fields);
  }
  return data as T;
}
