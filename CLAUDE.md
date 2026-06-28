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
- Supabase free tier pauses after ~1 week of inactivity → auth "failed to fetch" + JWKS fetch fails on Railway. Restore in Supabase dashboard.
- `pyjwt.PyJWKClientError` is NOT a subclass of `InvalidTokenError` — must be caught explicitly before `ExpiredSignatureError` in `auth.py` or JWKS failures are silently swallowed.
- Next.js middleware matcher must be narrowed to `/app(.*)`, `/history(.*)`, `/auth(.*)` only — broad matcher calls `getUser()` on every public page, adding a Supabase round-trip to the landing page.

## Current blockers
- **Daily Anthropic spend cap** not set — required before soft launch (console.anthropic.com → API key → Usage limits, $5/day).
- **Railway `SUPABASE_URL`** — confirm set to `https://tljqzpqqkbveipnnuspu.supabase.co`; "could not verify session" on lint is a Railway→Supabase JWKS failure.

## Pending (priority order)
1. Confirm Railway `SUPABASE_URL` is set; smoke-test lint end-to-end in prod.
2. Set $5/day Anthropic spend cap.
3. PostHog analytics (rubric firing rates, rewrite acceptance, abandonment).
4. Methodology writeup linked from README.
5. Soft launch to Metaculus / EA Forum / forecasting communities.
6. Phase 5: pilot with Metaculus authors → Sacramento civic orgs → case study.
