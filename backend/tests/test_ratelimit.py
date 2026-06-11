"""Tests for the Upstash rate-limit dependency.

httpx is mocked at the AsyncClient level so no real Upstash calls are made.
The auth dependency is stubbed via direct function calls (no FastAPI app
needed for unit-level tests of check_rate_limit logic)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from sharper.ratelimit import (
    ANONYMOUS_LIMIT_PER_HOUR,
    AUTHENTICATED_LIMIT_PER_HOUR,
    _bucket_key,
    _client_ip,
    _identity_key_for,
    check_rate_limit,
    is_configured,
)


# ----- Test fixtures --------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None, client_host: str | None = "1.2.3.4") -> Request:
    header_list = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/api/lint",
        "headers": header_list,
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
    }
    if client_host:
        scope["client"] = (client_host, 12345)
    return Request(scope)


def _call(request: Request, identity: str) -> None:
    """Run the dependency synchronously for assertion."""
    asyncio.run(check_rate_limit(request=request, identity=identity))


# ----- is_configured -------------------------------------------------------


def test_is_configured_false_when_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "tok")
    assert is_configured() is False


def test_is_configured_false_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://x.upstash.io")
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://x.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "tok")
    assert is_configured() is True


# ----- _client_ip -----------------------------------------------------------


def test_client_ip_from_xff_header() -> None:
    req = _make_request({"x-forwarded-for": "9.9.9.9, 10.0.0.1, 10.0.0.2"})
    assert _client_ip(req) == "9.9.9.9"


def test_client_ip_falls_back_to_direct_client() -> None:
    req = _make_request(headers={}, client_host="5.6.7.8")
    assert _client_ip(req) == "5.6.7.8"


def test_client_ip_unknown_when_no_client() -> None:
    req = _make_request(headers={}, client_host=None)
    assert _client_ip(req) == "unknown"


# ----- _identity_key_for ---------------------------------------------------


def test_identity_key_anonymous_uses_ip() -> None:
    req = _make_request({"x-forwarded-for": "9.9.9.9"})
    key, limit = _identity_key_for("anonymous-dev", req)
    assert key == "ip:9.9.9.9"
    assert limit == ANONYMOUS_LIMIT_PER_HOUR


def test_identity_key_authenticated_uses_identity() -> None:
    req = _make_request()
    key, limit = _identity_key_for("user_abc123", req)
    assert key == "id:user_abc123"
    assert limit == AUTHENTICATED_LIMIT_PER_HOUR


def test_identity_key_static_token_authenticated() -> None:
    req = _make_request()
    key, limit = _identity_key_for("shared-token", req)
    assert key == "id:shared-token"
    assert limit == AUTHENTICATED_LIMIT_PER_HOUR


def test_bucket_key_includes_hour_window() -> None:
    """Sanity: bucket key contains 'h<int>'."""
    k = _bucket_key("ip:1.2.3.4")
    assert k.startswith("ratelimit:ip:1.2.3.4:h")
    suffix = k.rsplit("h", 1)[-1]
    assert suffix.isdigit()


# ----- check_rate_limit (with mocked Upstash) ------------------------------


def _patch_upstash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "tok")


class _FakeResponse:
    def __init__(self, json_data: Any, status_code: int = 200):
        self._json = json_data
        self.status_code = status_code

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)  # type: ignore[arg-type]


def _fake_client(post_response: _FakeResponse | Exception) -> MagicMock:
    """Build a MagicMock that acts as `async with httpx.AsyncClient(...) as c`."""
    client = MagicMock()
    if isinstance(post_response, Exception):
        client.post = AsyncMock(side_effect=post_response)
    else:
        client.post = AsyncMock(return_value=post_response)
    # __aenter__ returns the client; __aexit__ returns None
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def test_no_op_when_upstash_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    req = _make_request()
    # Should not raise even though no Upstash is configured.
    _call(req, "user_abc")


def test_under_limit_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_upstash(monkeypatch)
    resp = _FakeResponse([{"result": 5}, {"result": 1}])
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(resp)):
        _call(_make_request(), "user_abc")  # 5 <= 60


def test_over_limit_raises_429_authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_upstash(monkeypatch)
    resp = _FakeResponse([{"result": AUTHENTICATED_LIMIT_PER_HOUR + 1}, {"result": 0}])
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(resp)):
        with pytest.raises(HTTPException) as exc:
            _call(_make_request(), "user_abc")
    assert exc.value.status_code == 429
    assert exc.value.headers.get("Retry-After") == "3600"


def test_over_limit_raises_429_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_upstash(monkeypatch)
    resp = _FakeResponse([{"result": ANONYMOUS_LIMIT_PER_HOUR + 1}, {"result": 0}])
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(resp)):
        with pytest.raises(HTTPException) as exc:
            _call(_make_request(), "anonymous-dev")
    assert exc.value.status_code == 429
    # Detail should mention the anonymous quota number (not the auth one)
    assert str(ANONYMOUS_LIMIT_PER_HOUR) in exc.value.detail


def test_fail_open_on_upstash_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Upstash raises, the dependency must NOT block the request."""
    _patch_upstash(monkeypatch)
    network_err = httpx.ConnectError("upstash unreachable")
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(network_err)):
        _call(_make_request(), "user_abc")  # no raise


def test_fail_open_on_upstash_bad_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Upstash returns garbage, the dependency must NOT block the request."""
    _patch_upstash(monkeypatch)
    resp = _FakeResponse({"not": "a list"})
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(resp)):
        _call(_make_request(), "user_abc")  # no raise


def test_fail_open_on_non_int_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_upstash(monkeypatch)
    resp = _FakeResponse([{"result": "not-an-int"}, {"result": 1}])
    with patch("sharper.ratelimit.httpx.AsyncClient", return_value=_fake_client(resp)):
        _call(_make_request(), "user_abc")  # no raise
