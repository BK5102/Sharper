"""Tests for the auth dependency (Supabase JWT + static bearer modes)."""

from __future__ import annotations

import asyncio
import time

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from sharper.auth import (
    _expected_static_token,
    _looks_like_jwt,
    _supabase_jwt_secret,
    is_configured,
    require_token,
)

# ---- helpers ----------------------------------------------------------------

_TEST_SECRET = "test-supabase-jwt-secret-at-least-32-chars-long"


def _make_token(
    sub: str = "user-uuid-123",
    audience: str = "authenticated",
    secret: str = _TEST_SECRET,
    expired: bool = False,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": audience,
        "iat": now - 10,
        "exp": now - 1 if expired else now + 3600,
        "role": "authenticated",
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _call(authorization: str | None) -> str:
    return asyncio.run(require_token(authorization=authorization))


# ---- _looks_like_jwt --------------------------------------------------------


def test_looks_like_jwt() -> None:
    assert _looks_like_jwt("aaa.bbb.ccc") is True
    assert _looks_like_jwt("eyJhbGc.eyJzdWI.signature") is True


def test_does_not_look_like_jwt() -> None:
    assert _looks_like_jwt("opaque-static-token-no-dots") is False
    assert _looks_like_jwt("xx.yy") is False
    assert _looks_like_jwt("xx.yy.zz.qq") is False
    assert _looks_like_jwt("aa..cc") is False


# ---- is_configured ----------------------------------------------------------


def test_is_configured_false_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_static_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


def test_is_configured_true_when_supabase_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    assert is_configured() is True


def test_is_configured_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


# ---- dev pass-through -------------------------------------------------------


def test_passthrough_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert _call(authorization=None) == "anonymous-dev"


# ---- static bearer ----------------------------------------------------------


def test_static_bearer_accepts_correct_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    assert _call(authorization="Bearer secret-static-token") == "shared-token"


def test_static_bearer_rejects_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    with pytest.raises(HTTPException) as exc:
        _call(authorization=None)
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail.lower()


def test_static_bearer_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    with pytest.raises(HTTPException) as exc:
        _call(authorization="Bearer wrong")
    assert exc.value.status_code == 401
    assert "invalid" in exc.value.detail.lower()


# ---- Supabase JWT -----------------------------------------------------------


def test_supabase_jwt_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    token = _make_token(sub="user-uuid-abc")
    assert _call(authorization=f"Bearer {token}") == "user-uuid-abc"


def test_supabase_jwt_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    token = _make_token(expired=True)
    with pytest.raises(HTTPException) as exc:
        _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_supabase_jwt_rejects_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    token = _make_token(secret="completely-different-secret-value-here")
    with pytest.raises(HTTPException) as exc:
        _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


def test_supabase_jwt_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    token = _make_token(audience="anon")
    with pytest.raises(HTTPException) as exc:
        _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


def test_supabase_jwt_rejects_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    with pytest.raises(HTTPException) as exc:
        _call(authorization=None)
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail.lower()


# ---- both configured: JWT wins, static is fallback --------------------------


def test_dual_mode_jwt_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback")
    token = _make_token(sub="user-uuid-xyz")
    assert _call(authorization=f"Bearer {token}") == "user-uuid-xyz"


def test_dual_mode_static_token_works_when_no_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback")
    assert _call(authorization="Bearer static-fallback") == "shared-token"
