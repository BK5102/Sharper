"""FastAPI wrapper around the linter.

Phase 3 entry. Single endpoint, no auth or rate limiting yet -- those land in
follow-ups (Clerk for auth, Upstash Redis for per-user/per-IP rate limit).

Run locally:
    sharper-api                            # uvicorn on 127.0.0.1:8000
    uvicorn sharper.api:app --reload       # equivalent, with auto-reload

Smoke test:
    curl -X POST http://127.0.0.1:8000/api/lint \\
         -H 'content-type: application/json' \\
         -d '{"question": "Will AI be a big deal by 2030?"}'
"""

from __future__ import annotations

import os
import sys

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .critic import MAX_INPUT_CHARS, critique_question
from .schema import Critique

# Load .env before the Anthropic client is constructed. override=True because the
# user's shell has ANTHROPIC_API_KEY exported as an empty string -- see PROMPT.md
# gotcha #3.
load_dotenv(override=True)

# Force UTF-8 on stdout so uvicorn logs with unicode (question text in error
# messages) render cleanly on Windows cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI(
    title="Sharper",
    version="0.1.0",
    description="Rubric-driven linter for forecasting questions.",
)

# CORS for the future Next.js frontend on localhost during dev.
# Tighten this for production deploys -- see PROMPT.md §10 for the deploy plan.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class LintRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=MAX_INPUT_CHARS,
        description=(
            f"The forecasting question to lint. Up to {MAX_INPUT_CHARS} characters. "
            "Real Metaculus questions fit easily."
        ),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe. No external dependencies hit."""
    return {"status": "ok", "version": app.version}


@app.post("/api/lint", response_model=Critique)
def lint(req: LintRequest) -> Critique:
    """Lint a forecasting question against the rubric."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty or whitespace-only")
    try:
        return critique_question(req.question)
    except ValueError as e:
        # critique_question raises on empty input or oversized input -- both 400.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except anthropic.APIStatusError as e:
        # Upstream API error from Anthropic. 502 is the right category.
        raise HTTPException(status_code=502, detail=f"upstream error: {e.message}") from e
    except anthropic.APIError as e:
        # Network / connection / other Anthropic SDK errors.
        raise HTTPException(status_code=502, detail=f"upstream error: {type(e).__name__}") from e


def run() -> None:
    """Console-script entry point: `sharper-api`."""
    import uvicorn

    host = os.getenv("SHARPER_API_HOST", "127.0.0.1")
    port = int(os.getenv("SHARPER_API_PORT", "8000"))
    uvicorn.run("sharper.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
