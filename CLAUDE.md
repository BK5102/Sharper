# Sharper

Writing linter for structured forecasting questions (Metaculus + civic/nonprofit). Paste a draft → rubric-driven critique naming the exact ambiguous phrase → suggested rewrites. Phases 1–3 complete and deployed. Phase 5 (civic mode) core shipped.

## Stack
- **Backend**: Python 3.11, FastAPI, Anthropic Sonnet (prompt caching), Supabase Postgres, Upstash Redis rate-limit, Sentry. Main entry: `sharper/api.py` (`POST /api/lint`, `GET /api/health`). Primary tuning lever: `sharper/rubric.py`. Hosted on Railway (Dockerfile, root dir `/backend`).
- **Frontend**: Next.js 16, React 19, Tailwind 4, TipTap. Auth via Supabase email+password. Middleware: `proxy.ts` (Next.js 16 renamed `middleware.ts`). Hosted on Vercel.
- Auth is Supabase — Clerk was removed in session 2.

## Dev commands (Git Bash / Windows)
```
cd backend && source .venv/Scripts/activate && pytest -v   # 113 tests
cd frontend && npm run build                               # must be 0 errors
```

## Commit rules
Plain messages only. No `Co-Authored-By: Claude` footer, no emoji.

## Critical gotchas
- `load_dotenv(override=True)` in every backend entry point — stale empty `ANTHROPIC_API_KEY` in shell.
- Railway: `builder = "DOCKERFILE"` in `railway.toml`; no `startCommand` (overrides Dockerfile CMD → 502).
- Supabase history page uses raw `fetch()` against PostgREST — no SDK (avoids realtime-js Vercel build failure).
- `_clear_auth_env` fixture in `test_api.py` clears Upstash vars between tests to prevent 429s.
- `SHARPER_ALLOWED_ORIGINS` env var must include the Vercel URL on Railway or CORS blocks the frontend.

## Current blockers
- `ANTHROPIC_API_KEY` not set on Railway → prod `/api/lint` returns 502 on every call.
- Daily Anthropic spend cap not yet set — required before soft launch.

## Pending (priority order)
1. Add `ANTHROPIC_API_KEY` to Railway, redeploy, smoke-test full flow.
2. Set $5/day spend cap at console.anthropic.com.
3. PostHog analytics (rubric firing rates, rewrite acceptance, abandonment).
4. Methodology writeup linked from README.
5. Soft launch to Metaculus / EA Forum / forecasting communities.
6. Phase 5: pilot with Metaculus authors → Sacramento civic orgs → case study.
