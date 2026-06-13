"""Tests for the auth dependency (Supabase JWT via JWKS + static bearer modes)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from sharper.auth import (
    _expected_static_token,
    _looks_like_jwt,
    _supabase_url,
    is_configured,
    require_token,
)

# ---- helpers ----------------------------------------------------------------

# RSA key pairs generated once per test session.
_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()
_WRONG_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

_TEST_SUPABASE_URL = "https://test.supabase.co"


def _make_token(
    sub: str = "user-uuid-123",
    audience: str = "authenticated",
    expired: bool = False,
    wrong_key: bool = False,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": audience,
        "iat": now - 10,
        "exp": now - 1 if expired else now + 3600,
        "role": "authenticated",
    }
    key = _WRONG_PRIVATE_KEY if wrong_key else _TEST_PRIVATE_KEY
    return pyjwt.encode(payload, key, algorithm="RS256")


def _mock_jwks_client() -> MagicMock:
    """Return a mock PyJWKClient whose signing key is the test public key."""
    mock_client = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = _TEST_PUBLIC_KEY
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    return mock_client


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
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_static_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


def test_is_configured_true_when_supabase_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    assert is_configured() is True


def test_is_configured_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    assert is_configured() is True


# ---- dev pass-through -------------------------------------------------------


def test_passthrough_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert _call(authorization=None) == "anonymous-dev"


# ---- static bearer ----------------------------------------------------------


def test_static_bearer_accepts_correct_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    assert _call(authorization="Bearer secret-static-token") == "shared-token"


def test_static_bearer_rejects_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    with pytest.raises(HTTPException) as exc:
        _call(authorization=None)
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail.lower()


def test_static_bearer_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-static-token")
    with pytest.raises(HTTPException) as exc:
        _call(authorization="Bearer wrong")
    assert exc.value.status_code == 401
    assert "invalid" in exc.value.detail.lower()


# ---- Supabase JWT (RS256 via JWKS) ------------------------------------------


def test_supabase_jwt_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    token = _make_token(sub="user-uuid-abc")
    with patch("sharper.auth._get_jwks_client", return_value=_mock_jwks_client()):
        assert _call(authorization=f"Bearer {token}") == "user-uuid-abc"


def test_supabase_jwt_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    token = _make_token(expired=True)
    with patch("sharper.auth._get_jwks_client", return_value=_mock_jwks_client()):
        with pytest.raises(HTTPException) as exc:
            _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_supabase_jwt_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    # Token signed with a different private key; mock returns the test public key → mismatch.
    token = _make_token(wrong_key=True)
    with patch("sharper.auth._get_jwks_client", return_value=_mock_jwks_client()):
        with pytest.raises(HTTPException) as exc:
            _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


def test_supabase_jwt_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    token = _make_token(audience="anon")
    with patch("sharper.auth._get_jwks_client", return_value=_mock_jwks_client()):
        with pytest.raises(HTTPException) as exc:
            _call(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


def test_supabase_jwt_rejects_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    with pytest.raises(HTTPException) as exc:
        _call(authorization=None)
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail.lower()


# ---- both configured: JWT wins, static is fallback --------------------------


def test_dual_mode_jwt_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback")
    token = _make_token(sub="user-uuid-xyz")
    with patch("sharper.auth._get_jwks_client", return_value=_mock_jwks_client()):
        assert _call(authorization=f"Bearer {token}") == "user-uuid-xyz"


def test_dual_mode_static_token_works_when_no_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", _TEST_SUPABASE_URL)
    monkeypatch.setenv("SHARPER_API_TOKEN", "static-fallback")
    assert _call(authorization="Bearer static-fallback") == "shared-token"
