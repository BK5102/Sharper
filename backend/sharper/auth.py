"""Authentication for /api/lint.

Two modes, picked by which env vars are set:

- **Supabase JWT** (set SUPABASE_URL). Verifies Bearer tokens as Supabase
  session JWTs by fetching the project's JWKS endpoint and validating the
  RS256/ES256 signature. Returns the user UUID from the `sub` claim.
  Production path — no secret to rotate; the public key is fetched from
  {SUPABASE_URL}/auth/v1/.well-known/jwks.json and cached in-process.
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
from jwt import PyJWKClient
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# Module-level JWKS client cache keyed by Supabase URL.
_JWKS_CLIENTS: dict[str, PyJWKClient] = {}


# ----- Env-var helpers -------------------------------------------------------


def _supabase_url() -> Optional[str]:
    val = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    return val or None


def _expected_static_token() -> Optional[str]:
    val = os.getenv("SHARPER_API_TOKEN", "").strip()
    return val or None


def is_configured() -> bool:
    """True iff at least one auth mode is configured."""
    return _supabase_url() is not None or _expected_static_token() is not None


# ----- JWT shape heuristic ---------------------------------------------------


def _looks_like_jwt(token: str) -> bool:
    """A Supabase session JWT has exactly three dot-separated base64url segments."""
    parts = token.split(".")
    return len(parts) == 3 and all(p for p in parts)


# ----- JWKS client -----------------------------------------------------------


def _get_jwks_client(supabase_url: str) -> PyJWKClient:
    if supabase_url not in _JWKS_CLIENTS:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        _JWKS_CLIENTS[supabase_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _JWKS_CLIENTS[supabase_url]


# ----- Supabase JWT verification ---------------------------------------------


def _verify_supabase_jwt(token: str) -> str:
    """Verify a Supabase session JWT via JWKS and return the user UUID.

    Raises HTTPException(401) on any verification failure.
    Raises HTTPException(503) if the JWKS endpoint is unreachable.
    """
    url = _supabase_url()
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        client = _get_jwks_client(url)
        signing_key = client.get_signing_key_from_jwt(token)
        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
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
    except Exception as e:
        logger.warning("JWKS fetch / JWT verify error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="could not verify session",
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
    supabase_url_val = _supabase_url()
    static_token = _expected_static_token()

    if supabase_url_val is None and static_token is None:
        return "anonymous-dev"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization: Bearer header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented = authorization.removeprefix("Bearer ").strip()

    # Supabase JWT path: try first when configured and token is JWT-shaped.
    if supabase_url_val is not None and _looks_like_jwt(presented):
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
