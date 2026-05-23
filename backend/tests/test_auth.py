"""Tests for the auth dependency. Pure-unit (no Clerk network calls -- the
clerk_backend_api SDK is mocked at the import boundary)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.requests import Request

from sharper.auth import (
    _expected_static_token,
    _looks_like_jwt,
    is_configured,
    require_token,
)


# ----- Test fixtures --------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request that satisfies Clerk's Requestish protocol."""
    header_list = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/lint",
        "headers": header_list,
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }
    return Request(scope)


def _call(request: Request, authorization: str | None) -> str:
    """Sync wrapper around the async dependency."""
    return asyncio.run(require_token(request=request, authorization=authorization))


# ----- _looks_like_jwt heuristic -------------------------------------------


def test_looks_like_jwt() -> None:
    assert _looks_like_jwt("aaa.bbb.ccc") is True
    assert _looks_like_jwt("eyJhbGc.eyJzdWI.signature") is True


def test_does_not_look_like_jwt() -> None:
    assert _looks_like_jwt("opaque-static-token-no-dots") is False
    assert _looks_like_jwt("xx.yy") is False  # two parts only
    assert _looks_like_jwt("xx.yy.zz.qq") is False  # four parts
    assert _looks_like_jwt("aa..cc") is False  # empty middle


# ----- is_configured -------------------------------------------------------


def test_is_configured_false_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_static_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


def test_is_configured_true_when_clerk_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    assert is_configured() is True


def test_is_configured_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


# ----- Mode D: nothing configured -> dev pass-through ----------------------


def test_passthrough_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    req = _make_request()
    assert _call(req, authorization=None) == "anonymous-dev"


# ----- Mode B: static bearer only ------------------------------------------


def test_static_bearer_accepts_correct_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    req = _make_request()
    assert _call(req, authorization="Bearer secret-static-token") == "shared-token"


def test_static_bearer_rejects_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    req = _make_request()
    with pytest.raises(HTTPException) as exc:
        _call(req, authorization=None)
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail.lower()


def test_static_bearer_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    req = _make_request()
    with pytest.raises(HTTPException) as exc:
        _call(req, authorization="Bearer wrong")
    assert exc.value.status_code == 401
    assert "invalid" in exc.value.detail.lower()


# ----- Mode A: Clerk only ---------------------------------------------------


def test_clerk_accepts_valid_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")

    fake_state = SimpleNamespace(is_signed_in=True, payload={"sub": "user_abc123"})

    async def fake_authenticate(req, opts):
        return fake_state

    with patch("clerk_backend_api.authenticate_request_async", new=fake_authenticate):
        req = _make_request({"authorization": "Bearer header.payload.sig"})
        assert _call(req, authorization="Bearer header.payload.sig") == "user_abc123"


def test_clerk_rejects_invalid_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")

    fake_state = SimpleNamespace(is_signed_in=False, payload=None, reason="session-token-expired")

    async def fake_authenticate(req, opts):
        return fake_state

    with patch("clerk_backend_api.authenticate_request_async", new=fake_authenticate):
        req = _make_request({"authorization": "Bearer expired.jwt.sig"})
        with pytest.raises(HTTPException) as exc:
            _call(req, authorization="Bearer expired.jwt.sig")
        assert exc.value.status_code == 401


def test_clerk_only_mode_rejects_missing_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clerk-only mode with no bearer in request -> 401."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    req = _make_request()
    with pytest.raises(HTTPException) as exc:
        _call(req, authorization=None)
    assert exc.value.status_code == 401
    assert "clerk" in exc.value.detail.lower() or "missing" in exc.value.detail.lower()


def test_clerk_only_mode_rejects_non_jwt_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clerk-only + a token without dots -> Clerk path is skipped, no static
    fallback, so we get 'missing Clerk session token'."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    req = _make_request({"authorization": "Bearer opaque-no-dots"})
    with pytest.raises(HTTPException) as exc:
        _call(req, authorization="Bearer opaque-no-dots")
    assert exc.value.status_code == 401


# ----- Mode C: both Clerk and static configured ----------------------------


def test_dual_mode_clerk_token_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT-shaped bearer -> Clerk path verifies and returns user_id."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback-token")

    fake_state = SimpleNamespace(is_signed_in=True, payload={"sub": "user_abc"})

    async def fake_authenticate(req, opts):
        return fake_state

    with patch("clerk_backend_api.authenticate_request_async", new=fake_authenticate):
        req = _make_request({"authorization": "Bearer hdr.pld.sig"})
        assert _call(req, authorization="Bearer hdr.pld.sig") == "user_abc"


def test_dual_mode_static_token_works_when_no_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Static-token-shaped bearer -> Clerk path skipped, static path accepts."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback-token")
    req = _make_request({"authorization": "Bearer static-fallback-token"})
    assert _call(req, authorization="Bearer static-fallback-token") == "shared-token"


def test_dual_mode_clerk_failure_falls_back_to_static(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT-shaped bearer but Clerk rejects -> falls through to static-bearer
    check, which will also reject because static expects exact match.

    Confirms the fallthrough path doesn't deadlock or skip the static check."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xyz")
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback-token")

    fake_state = SimpleNamespace(is_signed_in=False, payload=None, reason="invalid")

    async def fake_authenticate(req, opts):
        return fake_state

    with patch("clerk_backend_api.authenticate_request_async", new=fake_authenticate):
        # Bearer is JWT-shaped but Clerk says no. Falls to static. Static
        # compares "bad.jwt.sig" to "static-fallback-token" -> reject.
        req = _make_request({"authorization": "Bearer bad.jwt.sig"})
        with pytest.raises(HTTPException) as exc:
            _call(req, authorization="Bearer bad.jwt.sig")
        assert exc.value.status_code == 401
