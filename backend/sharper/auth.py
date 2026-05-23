"""Pre-Clerk auth gate for /api/lint.

Until Phase 3 step 3 lands (Clerk JWT verification with per-user identity), this
static-bearer-token gate is the only thing preventing an unauthenticated caller
from burning paid Anthropic credit on a deployed instance.

Behavior:
- If `SHARPER_API_TOKEN` env var is set: requests must include
  `Authorization: Bearer <that-token>`. Mismatched or missing token -> 401.
- If `SHARPER_API_TOKEN` is unset: requests pass through (returns "anonymous-dev").
  This keeps local development frictionless. The `api.run()` entrypoint refuses
  to bind to a non-loopback host when the token is unset, so a publicly-exposed
  deploy cannot ship with this fallback active.

Token generation (run on the deploy machine, paste output into backend/.env):
    python -c "import secrets; print(secrets.token_urlsafe(32))"

Token comparison uses `secrets.compare_digest` to prevent timing side channels.

This file disappears when Clerk lands -- the dependency becomes a JWKS verifier
that returns a real user_id. Keep the dependency signature stable
(`async def require_token(...) -> str`) so swapping the implementation is a
single-file change.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status


def _expected_token() -> str | None:
    val = os.getenv("SHARPER_API_TOKEN", "").strip()
    return val or None


def is_configured() -> bool:
    """True iff SHARPER_API_TOKEN is set to a non-empty value."""
    return _expected_token() is not None


async def require_token(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: require a valid Bearer token, or fall through if not configured.

    Returns a placeholder identity string. When Clerk lands, the dependency
    will return a real `user_id` extracted from the verified JWT.
    """
    expected = _expected_token()
    if expected is None:
        return "anonymous-dev"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization: Bearer <token> header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    presented = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "shared-token"
