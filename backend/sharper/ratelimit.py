"""Per-identity hourly rate limiter backed by Upstash Redis REST.

Wall-clock fixed-window counter. The key is `ratelimit:<id>:h<hour>` where
`hour = int(time.time()) // 3600`. Each request INCRs the counter; the first
INCR also sets a 1-hour TTL on the key (NX so we don't reset the window
mid-bucket). When the counter exceeds the per-identity quota, the dependency
raises 429 with a `Retry-After: 3600` header.

Quotas:
  - Anonymous (no Clerk session, no static bearer): ANONYMOUS_LIMIT_PER_HOUR
  - Authenticated (Clerk user_id or static shared-token): AUTHENTICATED_LIMIT_PER_HOUR

Failure mode: fail-open. If Upstash is unreachable / returns a bad shape, we
log and pass the request through. For an MVP this is the right tradeoff -- we
don't want the linter to go down because rate-limiting infra is degraded. A
production setup might want fail-closed; flip the early `return` to a raise.

Configuration: requires UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN.
When either is missing the dependency is a no-op (useful for local dev /
tests / pre-Upstash deploys).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status

from . import auth

logger = logging.getLogger(__name__)


# ----- Configuration -------------------------------------------------------


def _upstash_url() -> Optional[str]:
    val = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    return val or None


def _upstash_token() -> Optional[str]:
    val = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    return val or None


def is_configured() -> bool:
    return _upstash_url() is not None and _upstash_token() is not None


# Quotas. Source of truth for the spec's "10 req/hr anonymous" cost control.
ANONYMOUS_LIMIT_PER_HOUR = 10
AUTHENTICATED_LIMIT_PER_HOUR = 60

# Sentinel identity strings returned by auth.require_token when no real
# user is identified. Treat as anonymous for rate-limit purposes.
_ANONYMOUS_IDENTITIES = {"anonymous-dev"}


# ----- Key derivation ------------------------------------------------------


def _client_ip(request: Request) -> str:
    """Best-effort caller IP. Honors X-Forwarded-For when behind a proxy
    (Railway, Cloudflare), else falls back to the direct client address."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        # Leftmost address is the original client; rest is the proxy chain.
        first = fwd.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _bucket_key(identity_key: str) -> str:
    hour = int(time.time()) // 3600
    return f"ratelimit:{identity_key}:h{hour}"


def _identity_key_for(identity: str, request: Request) -> tuple[str, int]:
    """Returns (key_id, hourly_quota) for the calling identity.

    Anonymous (dev-only since the api.run() guard refuses non-loopback bind
    in this case) is keyed by IP; authenticated is keyed by the
    auth-returned identity string (Clerk user_id or 'shared-token').
    """
    if identity in _ANONYMOUS_IDENTITIES:
        return f"ip:{_client_ip(request)}", ANONYMOUS_LIMIT_PER_HOUR
    return f"id:{identity}", AUTHENTICATED_LIMIT_PER_HOUR


# ----- Upstash REST call ---------------------------------------------------


async def _incr_with_ttl(key: str, ttl_seconds: int) -> Optional[int]:
    """Atomically INCR the key and set TTL (NX, so it doesn't reset mid-bucket).

    Returns the new counter value on success; None on Upstash failure
    (which the caller interprets as fail-open).
    """
    url = _upstash_url()
    token = _upstash_token()
    if not url or not token:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # Upstash REST pipeline: list of command-arg arrays. The response is a
    # list of {"result": ...} or {"error": ...} entries.
    pipeline = [
        ["INCR", key],
        ["EXPIRE", key, str(ttl_seconds), "NX"],
    ]
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(f"{url}/pipeline", headers=headers, json=pipeline)
            resp.raise_for_status()
            results = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("upstash rate-limit call failed (fail-open): %s: %s", type(e).__name__, e)
        return None

    if not isinstance(results, list) or not results:
        logger.warning("upstash pipeline returned unexpected shape: %r", results)
        return None
    incr_entry = results[0]
    if not isinstance(incr_entry, dict) or "result" not in incr_entry:
        logger.warning("upstash INCR returned unexpected shape: %r", incr_entry)
        return None
    try:
        return int(incr_entry["result"])
    except (TypeError, ValueError):
        return None


# ----- FastAPI dependency --------------------------------------------------


async def check_rate_limit(
    request: Request,
    identity: str = Depends(auth.require_token),
) -> None:
    """Increment the caller's hourly counter; raise 429 when over quota.

    Composes auth.require_token so the route's auth check runs first (FastAPI
    dedups dependency results within a request). When Upstash is unconfigured
    or fails, this is a no-op (fail-open).
    """
    if not is_configured():
        return

    key_id, limit = _identity_key_for(identity, request)
    count = await _incr_with_ttl(_bucket_key(key_id), ttl_seconds=3600)
    if count is None:
        # Upstash didn't respond cleanly. Fail-open.
        return
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"rate limit exceeded ({limit} requests/hour for this identity)",
            headers={"Retry-After": "3600"},
        )
