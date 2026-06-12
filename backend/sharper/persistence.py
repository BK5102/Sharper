"""Supabase persistence layer for Phase 3 step 5.

Uses the Supabase PostgREST REST API directly via httpx — no supabase-py SDK.
This mirrors the ratelimit.py pattern (Upstash via httpx) and avoids adding a
large SDK dependency that has caused Railway build failures on Python 3.13.

Writes one critique + its findings to Supabase on each successful lint call.
Fail-open: if Supabase is unreachable or not configured, the lint response
still returns normally. A warning is logged but no exception is raised.

SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment.
When either is missing this module is a no-op (local dev without Supabase).

The service-role key bypasses Supabase RLS, which is intentional -- all DB
access goes through this backend, never via browser-side Supabase clients.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .schema import Critique

logger = logging.getLogger("sharper.persistence")


def _config() -> tuple[str, str] | None:
    """Return (url, service_role_key) or None when not configured."""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url, key
    logger.debug("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — persistence disabled")
    return None


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def save_critique(user_id: str, question: str, critique: "Critique") -> str | None:
    """Persist a completed critique and its findings via Supabase REST.

    Returns the new critique UUID on success, None on any failure.
    Never raises — callers must not depend on this succeeding.
    """
    cfg = _config()
    if cfg is None:
        return None

    url, key = cfg
    headers = _headers(key)

    try:
        with httpx.Client(timeout=5.0) as client:
            # Insert critique row; Prefer: return=representation gives us the
            # generated UUID back in the response body.
            resp = client.post(
                f"{url}/rest/v1/critiques",
                headers={**headers, "Prefer": "return=representation"},
                json={
                    "user_id": user_id,
                    "question": question,
                    "overall_assessment": critique.overall_assessment,
                },
            )
            resp.raise_for_status()
            critique_id: str = resp.json()[0]["id"]

            if critique.findings:
                resp2 = client.post(
                    f"{url}/rest/v1/findings",
                    headers={**headers, "Prefer": "return=minimal"},
                    json=[
                        {
                            "critique_id": critique_id,
                            "rubric_item": f.rubric_item.value,
                            "severity": f.severity.value,
                            "quoted_span": f.quoted_span,
                            "issue": f.issue,
                            "explanation": f.explanation,
                            "suggested_rewrite": f.suggested_rewrite,
                        }
                        for f in critique.findings
                    ],
                )
                resp2.raise_for_status()

        logger.debug(
            "Saved critique %s for user %s (%d findings)",
            critique_id, user_id, len(critique.findings),
        )
        return critique_id

    except Exception as e:
        logger.warning("Supabase write failed (critique not persisted): %s: %s", type(e).__name__, e)
        return None
