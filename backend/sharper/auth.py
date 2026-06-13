"""Authentication for /api/lint.

Two modes, picked by which env vars are set:

- **Supabase JWT** (set SUPABASE_JWT_SECRET). Verifies the Bearer token as a
  Supabase session JWT (HS256) and returns the user UUID from the `sub` claim.
  Production path.
- **Static bearer** (set SHARPER_API_TOKEN). Pre-shared token, constant-time
  comparison. Returns "shared-token" as the user_id placeholder. Useful for
  service-to-service calls and local dev.

If neither is set, requests pass through as "anonymous-dev" — only safe on
loopback. `api.run()` refuses to bind to a non-loopback host when neither
is configured.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

import jwt as pyjwt
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


# ----- Env-var helpers -------------------------------------------------------


def _supabase_jwt_secret() -> Optional[str]:
    val = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    return val or None


def _expected_static_token() -> Optional[str]:
    val = os.getenv("SHARPER_API_TOKEN", "").strip()
    return val or None


def is_configured() -> bool:
    """True iff at least one auth mode is configured."""
    return _supabase_jwt_secret() is not None or _expected_static_token() is not None


# ----- JWT shape heuristic ---------------------------------------------------


def _looks_like_jwt(token: str) -> bool:
    """A Supabase session JWT has exactly three dot-separated base64url segments."""
    parts = token.split(".")
    return len(parts) == 3 and all(p for p in parts)


# ----- Supabase JWT verification --------------------------------------------


def _verify_supabase_jwt(token: str) -> str:
    """Verify a Supabase session JWT and return the user UUID.

    Raises HTTPException(401) on any verification failure.
    """
    secret = _supabase_jwt_secret()
    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as e:
        logger.info("supabase JWT invalid: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        logger.warning("supabase JWT verified but missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session token missing user identity",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# ----- The FastAPI dependency ------------------------------------------------


async def require_token(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Verify Supabase JWT or static bearer; return a user-id-like string.

    Returns:
      - The Supabase user UUID when a Supabase JWT verifies.
      - "shared-token" when the static SHARPER_API_TOKEN matches.
      - "anonymous-dev" when no auth is configured (loopback-only).

    Raises HTTPException(401) when auth is configured but the request fails it.
    """
    supabase_secret = _supabase_jwt_secret()
    static_token = _expected_static_token()

    # Nothing configured -> dev pass-through.
    if supabase_secret is None and static_token is None:
        return "anonymous-dev"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization: Bearer header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented = authorization.removeprefix("Bearer ").strip()

    # Supabase JWT path: try first when configured and token is JWT-shaped.
    if supabase_secret is not None and _looks_like_jwt(presented):
        return _verify_supabase_jwt(presented)

    # Static bearer path.
    if static_token is not None:
        if secrets.compare_digest(presented, static_token):
            return "shared-token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Supabase is configured but token doesn't look like a JWT.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing valid session token",
        headers={"WWW-Authenticate": "Bearer"},
    )
