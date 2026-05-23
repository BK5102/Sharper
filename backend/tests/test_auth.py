"""Tests for the bearer-token gate. Pure-unit (no network)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from sharper.auth import _expected_token, is_configured, require_token


def _call_require_token(authorization: str | None) -> str:
    """Sync wrapper around the async dependency for testing.

    Avoids needing pytest-asyncio as an extra dev dep.
    """
    return asyncio.run(require_token(authorization=authorization))


# ----- _expected_token / is_configured --------------------------------------


def test_is_configured_false_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert _expected_token() is None
    assert is_configured() is False


def test_is_configured_false_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "   ")
    assert _expected_token() is None
    assert is_configured() is False


def test_is_configured_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "abc123")
    assert _expected_token() == "abc123"
    assert is_configured() is True


# ----- require_token --------------------------------------------------------


def test_require_token_passes_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SHARPER_API_TOKEN is unset, requests pass through (anonymous-dev)."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    assert _call_require_token(None) == "anonymous-dev"


def test_require_token_passes_with_correct_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-token-123")
    assert _call_require_token("Bearer secret-token-123") == "shared-token"


def test_require_token_rejects_missing_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-token-123")
    with pytest.raises(HTTPException) as exc_info:
        _call_require_token(None)
    assert exc_info.value.status_code == 401
    assert "missing" in exc_info.value.detail.lower()
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


def test_require_token_rejects_non_bearer_scheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-token-123")
    with pytest.raises(HTTPException) as exc_info:
        _call_require_token("Basic dXNlcjpwYXNz")
    assert exc_info.value.status_code == 401


def test_require_token_rejects_wrong_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "secret-token-123")
    with pytest.raises(HTTPException) as exc_info:
        _call_require_token("Bearer wrong-token")
    assert exc_info.value.status_code == 401
    assert "invalid" in exc_info.value.detail.lower()


def test_require_token_uses_constant_time_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity check that compare_digest is in the code path."""
    import secrets as _secrets

    monkeypatch.setenv("SHARPER_API_TOKEN", "abc")
    with patch("sharper.auth.secrets.compare_digest", wraps=_secrets.compare_digest) as mock:
        _call_require_token("Bearer abc")
        assert mock.called
