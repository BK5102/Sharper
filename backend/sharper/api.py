"""FastAPI wrapper around the linter.

Phase 3 entry. Hardened pre-Clerk with a static-bearer auth gate, body size
cap, security headers, and sanitized upstream-error responses. The real auth
(Clerk JWT verification, per-user identity) lands in Phase 3 step 3.

Run locally:
    sharper-api                            # uvicorn on 127.0.0.1:8000
    uvicorn sharper.api:app --reload       # equivalent, with auto-reload

Smoke test (no auth token configured):
    curl -X POST http://127.0.0.1:8000/api/lint \\
         -H 'content-type: application/json' \\
         -d '{"question": "Will AI be a big deal by 2030?"}'

With auth (SHARPER_API_TOKEN set in env):
    curl -X POST http://127.0.0.1:8000/api/lint \\
         -H 'content-type: application/json' \\
         -H "authorization: Bearer $SHARPER_API_TOKEN" \\
         -d '{"question": "..."}'
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from . import auth
from .critic import MAX_INPUT_CHARS, critique_question
from .schema import Critique

# Load .env before the Anthropic client is constructed. override=True because the
# user's shell has ANTHROPIC_API_KEY exported as an empty string -- see the
# project-local PROMPT.md gotcha #3.
load_dotenv(override=True)

# Force UTF-8 on stdout so uvicorn logs with unicode (question text in error
# messages) render cleanly on Windows cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger("sharper.api")

# Request body cap. MAX_INPUT_CHARS = 4000; JSON wrapper + headers adds ~1KB.
# 16KB leaves 4x headroom and is 64,000x smaller than what a careless attacker
# might POST. Reject larger bodies before Pydantic parses them.
MAX_BODY_BYTES = 16 * 1024


# ----- Middleware -----------------------------------------------------------


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared Content-Length exceeds the cap.

    Only inspects the Content-Length header (which all sane JSON clients send).
    Chunked / streaming uploads bypass this check; for those, Pydantic's
    field-level max_length still applies after the body is fully parsed.
    """

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        {"detail": f"request body exceeds {self.max_bytes}-byte limit"},
                        status_code=413,
                    )
            except ValueError:
                pass
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set conservative security headers on every response.

    JSON API only, so CSP is unnecessary (browsers don't enforce CSP on JSON).
    X-Frame-Options is set to DENY since this API is never meant to be embedded.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "interest-cohort=()"
        return response


# ----- Lifespan / startup config check --------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Log clear warnings if security-relevant env is missing.

    These do not refuse startup -- local dev should be frictionless. The
    `run()` entrypoint refuses non-loopback bind when SHARPER_API_TOKEN is
    unset (see below) so a public deploy can't accidentally ship without auth.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error(
            "SECURITY: ANTHROPIC_API_KEY is not set. /api/lint will return 502 "
            "on every call until it is configured."
        )
    if not auth.is_configured():
        logger.warning(
            "SECURITY: SHARPER_API_TOKEN is not set. /api/lint is reachable "
            "without authentication. This is OK on localhost only -- the run() "
            "entrypoint refuses non-loopback binds when the token is unset."
        )
    yield


# ----- App ------------------------------------------------------------------

app = FastAPI(
    title="Sharper",
    version="0.1.0",
    description="Rubric-driven linter for forecasting questions.",
    lifespan=lifespan,
)

# Middlewares apply in reverse order of registration. SecurityHeaders is added
# last so it runs first on response -- guaranteed to set headers regardless of
# what other middleware does.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_BODY_BYTES)
app.add_middleware(SecurityHeadersMiddleware)

# CORS. allow_origins is explicit (not "*"); allow_headers is tightened to the
# only two headers the frontend sends. Production deploy must extend
# allow_origins to include the Vercel URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "authorization"],
)


# ----- Models ---------------------------------------------------------------


class LintRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=MAX_INPUT_CHARS,
        description=(
            f"The forecasting question to lint. Up to {MAX_INPUT_CHARS} characters. "
            "Real Metaculus questions fit easily."
        ),
    )


# ----- Routes ---------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe. No external dependencies hit, no auth required."""
    return {"status": "ok", "version": app.version}


@app.post("/api/lint", response_model=Critique)
def lint(
    req: LintRequest,
    _identity: str = Depends(auth.require_token),
) -> Critique:
    """Lint a forecasting question against the rubric.

    Requires `Authorization: Bearer <SHARPER_API_TOKEN>` when the server is
    configured with a token. When `SHARPER_API_TOKEN` is unset, falls through
    (anonymous dev mode -- only safe on localhost).
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty or whitespace-only")
    try:
        return critique_question(req.question)
    except ValueError as e:
        # critique_question raises on empty/oversized input.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except anthropic.APIStatusError as e:
        # Log details server-side; return a generic categorized message to the
        # client. We deliberately do NOT echo `e.message` -- it can carry context
        # about the request (model, partial prompt) that we don't need to expose.
        logger.exception("anthropic APIStatusError: status=%s", e.status_code)
        if 400 <= e.status_code < 500:
            raise HTTPException(
                status_code=502, detail="upstream API rejected the request"
            ) from e
        raise HTTPException(status_code=502, detail="upstream API unavailable") from e
    except anthropic.APIError as e:
        logger.exception("anthropic APIError: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail="upstream API error") from e


# ----- Entrypoint -----------------------------------------------------------


def run() -> None:
    """Console-script entry point: `sharper-api`.

    Refuses to bind to a non-loopback host when SHARPER_API_TOKEN is unset.
    Set both env vars together when deploying:
        SHARPER_API_HOST=0.0.0.0
        SHARPER_API_TOKEN=<long random string>
    """
    import uvicorn

    host = os.getenv("SHARPER_API_HOST", "127.0.0.1")
    port = int(os.getenv("SHARPER_API_PORT", "8000"))
    if host not in ("127.0.0.1", "localhost", "::1") and not auth.is_configured():
        raise SystemExit(
            f"refusing to bind to host={host!r} without SHARPER_API_TOKEN set. "
            "Set the token in backend/.env first, then retry. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    uvicorn.run("sharper.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
