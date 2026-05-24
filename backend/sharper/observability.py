"""Sentry SDK initialization + PII scrubbing.

Belt-and-suspenders defense against leaking user-pasted forecasting questions
to the error tracker:

1. `sentry_sdk.init(send_default_pii=False)` — Sentry's default-off mode.
   Request bodies, headers, cookies, IP addresses are not included in events.
2. `before_send=scrub_question_field` — explicit scrubber that finds any
   `question` field in the event payload and replaces it with `[SCRUBBED]`.
   Catches anything that might slip past send_default_pii (e.g. if we ever
   capture exceptions whose repr happens to include the question text, or
   if the SDK's default behavior changes in a future release).

Init is a no-op when `SENTRY_DSN` is unset, so local dev and the test suite
don't need a Sentry account.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SCRUBBED_KEYS = {"question"}
_SCRUBBED_MARKER = "[SCRUBBED]"


def scrub_question_field(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sentry before_send hook: remove the user's `question` text from events.

    Walks the standard Sentry event payload paths where request bodies land:
      event["request"]["data"] — dict or stringified JSON
    Replaces any `question` key found with the marker.
    """
    request = event.get("request")
    if not isinstance(request, dict):
        return event
    data = request.get("data")
    if isinstance(data, dict):
        for key in _SCRUBBED_KEYS:
            if key in data:
                data[key] = _SCRUBBED_MARKER
    elif isinstance(data, str):
        # JSON-stringified body; try to parse, scrub, re-emit.
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return event
        if isinstance(parsed, dict):
            dirty = False
            for key in _SCRUBBED_KEYS:
                if key in parsed:
                    parsed[key] = _SCRUBBED_MARKER
                    dirty = True
            if dirty:
                request["data"] = json.dumps(parsed)
    return event


def init_sentry() -> bool:
    """Initialize Sentry if SENTRY_DSN is set. Returns True iff initialized.

    Safe to call multiple times (Sentry init is idempotent for the same DSN).
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.utils import BadDsn
    except ImportError as e:
        logger.error("sentry-sdk not installed despite SENTRY_DSN set: %s", e)
        return False

    # Reject obvious placeholders so a copy of .env.example doesn't blow up the
    # app at import time. Common shapes from the template:
    #   https://...@o000000.ingest.sentry.io/0000000
    #   https://<key>@<org>.ingest.sentry.io/<project>
    if "..." in dsn or "o000000" in dsn or "<" in dsn:
        logger.warning("SENTRY_DSN looks like a placeholder (%s...); skipping init", dsn[:30])
        return False

    environment = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT") or "development"
    release = os.getenv("SENTRY_RELEASE") or os.getenv("RAILWAY_GIT_COMMIT_SHA")

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            send_default_pii=False,  # do NOT capture request bodies, headers, IP
            traces_sample_rate=0.1,  # 10% transaction sampling
            before_send=scrub_question_field,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
        )
    except BadDsn as e:
        # Malformed DSN -- log loudly but don't crash the app at import time.
        logger.error("Sentry init failed: invalid DSN (%s)", e)
        return False
    logger.info("Sentry initialized: env=%s release=%s", environment, (release or "unset")[:12])
    return True
