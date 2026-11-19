import httpx
import pytest

from md2short._retry import APIError, post_with_retry


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_retries_429_5xx_then_succeeds_with_backoffs():
    calls, sleeps = [], []
    codes = iter([429, 503, 500, 200])

    def handler(req):
        calls.append(1)
        return httpx.Response(next(codes), text="ok")

    r = post_with_retry(_client(handler), "https://x.test/a", timeout=1, sleep=sleeps.append, json={})
    assert r.status_code == 200
    assert len(calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_exhausted_retries_raise():
    calls, sleeps = [], []

    def handler(req):
        calls.append(1)
        return httpx.Response(502, text="bad gateway")

    with pytest.raises(APIError, match="502"):
        post_with_retry(_client(handler), "https://x.test/a", timeout=1, sleep=sleeps.append)
    assert len(calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_timeout_and_transport_errors_retried():
    seq = iter([httpx.ReadTimeout("t"), httpx.ConnectError("c"), None])
    sleeps = []

    def handler(req):
        e = next(seq)
        if e:
            raise e
        return httpx.Response(200)

    r = post_with_retry(_client(handler), "https://x.test/a", timeout=1, sleep=sleeps.append)
    assert r.status_code == 200
    assert sleeps == [0.5, 1.0]


def test_non_retryable_4xx_raises_immediately_with_body():
    calls, sleeps = [], []

    def handler(req):
        calls.append(1)
        return httpx.Response(401, text="invalid api key xyz")

    with pytest.raises(APIError, match="invalid api key xyz") as ei:
        post_with_retry(_client(handler), "https://x.test/a", timeout=1, sleep=sleeps.append)
    assert ei.value.status_code == 401
    assert len(calls) == 1 and sleeps == []


def test_transport_error_exhausted_raises_api_error():
    def handler(req):
        raise httpx.ConnectError("down")

    with pytest.raises(APIError, match="ConnectError"):
        post_with_retry(_client(handler), "https://x.test/a", timeout=1, sleep=lambda s: None)
