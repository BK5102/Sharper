"""Supabase persistence layer for Phase 3 step 5.

Writes one critique + its findings to Supabase on each successful lint call.
Fail-open: if Supabase is unreachable or not configured, the lint response
still returns normally. A warning is logged but no exception is raised.

The module holds a lazily-created singleton client. SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY must be set in the environment (or backend/.env).
When either is missing the module is a no-op (local dev without Supabase).

The service-role key bypasses Supabase RLS, which is intentional -- all DB
access goes through this backend, never via browser-side Supabase clients.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

    from .schema import Critique

logger = logging.getLogger("sharper.persistence")

_client: "Client | None" = None
_client_init_attempted = False


def _get_client() -> "Client | None":
    global _client, _client_init_attempted
    if _client_init_attempted:
        return _client

    _client_init_attempted = True
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        logger.debug("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — persistence disabled")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialized (url=%s)", url)
    except Exception as e:
        logger.warning("Failed to initialize Supabase client: %s", e)

    return _client


def save_critique(user_id: str, question: str, critique: "Critique") -> str | None:
    """Persist a completed critique and its findings.

    Returns the new critique UUID on success, None on any failure.
    Never raises — callers must not depend on this succeeding.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        row = client.table("critiques").insert(
            {
                "user_id": user_id,
                "question": question,
                "overall_assessment": critique.overall_assessment,
            }
        ).execute()

        critique_id: str = row.data[0]["id"]

        if critique.findings:
            client.table("findings").insert(
                [
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
                ]
            ).execute()

        logger.debug("Saved critique %s for user %s (%d findings)", critique_id, user_id, len(critique.findings))
        return critique_id

    except Exception as e:
        logger.warning("Supabase write failed (critique not persisted): %s", e)
        return None
