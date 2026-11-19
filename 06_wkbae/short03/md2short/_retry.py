"""외부 API 재시도 래퍼 (architecture.md §2.2): 429/5xx/timeout/transport 에러 최대 3회, 0.5/1.0/2.0s backoff."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

RETRY_BACKOFFS: tuple[float, ...] = (0.5, 1.0, 2.0)
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 120.0


class APIError(RuntimeError):
    """재시도 불가 또는 재시도 소진된 API 오류."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _retryable_status(code: int) -> bool:
    return code == 429 or code >= 500


def post_with_retry(
    client_or_none: httpx.Client | None,
    url: str,
    *,
    retries: int = DEFAULT_RETRIES,
    backoffs: tuple[float, ...] = RETRY_BACKOFFS,
    timeout: float = DEFAULT_TIMEOUT,
    sleep: Callable[[float], None] = time.sleep,
    **request_kwargs: Any,
) -> httpx.Response:
    """POST 후 성공 응답을 반환한다. 재시도 소진/비재시도 4xx 는 APIError."""
    own_client = client_or_none is None
    client = httpx.Client(timeout=timeout) if own_client else client_or_none
    last_error = "unknown error"
    try:
        for attempt in range(retries + 1):
            try:
                resp = client.post(url, timeout=timeout, **request_kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                status = None
            else:
                if resp.is_success:
                    return resp
                body = resp.text[:2000]
                last_error = f"HTTP {resp.status_code}: {body}"
                status = resp.status_code
                if not _retryable_status(resp.status_code):
                    raise APIError(f"POST {url} failed: {last_error}", status)
            if attempt < retries:
                sleep(backoffs[min(attempt, len(backoffs) - 1)])
        raise APIError(f"POST {url} failed after {retries} retries: {last_error}", status)
    finally:
        if own_client:
            client.close()
