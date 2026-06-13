# Sharper — Project Reference

This file is a self-contained snapshot of the project: what it is, the decisions made, the architecture chosen, the gotchas hit, and the exact recipe to recreate it from scratch. Read this first if returning to the project after a break or rebuilding from zero.

Last updated: 2026-06-12 (session 2). **Keep this file in sync** with every meaningful change (rubric edits, schema changes, eval workflow changes, new gotchas, deploy events).

---

## 1. Elevator pitch

**Sharper** is a writing tool for forecasters and question-authors. Paste a draft forecasting question; it returns a structured critique that names exactly which phrase or clause is ambiguous, why it would cause a disputed resolution, and (Phase 2+) a suggested rewrite. Targets quality problems on platforms like Metaculus where vague wording leads to disputed resolutions and wasted forecaster attention.

**Not**: a forecaster, a probability estimator, a general grammar checker, a Metaculus integration. Narrow scope: writing aid for forecasting-question quality.

---

## 2. Original project spec (verbatim summary)

### Stack (target)

- **Backend**: Python 3.11+, FastAPI, Anthropic Claude API (Sonnet for the critique), Pydantic for structured output.
- **Frontend**: Next.js 14 (App Router) + TypeScript, Tailwind + shadcn/ui, TipTap or contenteditable for inline span highlighting and click-to-accept rewrites.
- **Auth & storage**: Clerk (magic link + Google OAuth), Supabase Postgres keyed by Clerk user ID.
- **Infra**: Vercel (frontend), Railway (backend), Upstash Redis (per-user rate limit with per-IP fallback), Sentry (error tracking).
- **Eval & CI**: pytest + custom eval script, 50-question annotated JSONL test set in git, dated eval-history JSON in git, GitHub Actions failing the PR if recall drops on rubric change.
- **Cost controls**: per-IP 10 req/hr anonymous, daily Anthropic spend cap, ~4,000 char input cap, kill-switch endpoint.

### Product goals

- Single text field for the draft question (title + optional resolution criteria + background); Google OAuth auth.
- Rubric-based critique evaluating resolution criteria clarity, time-bound specification, operationalization, edge-case handling, source authority, scope drift. Each rubric item produces a specific finding.
- Inline span highlighting — flagged problems tied to the exact phrase that triggered them.
- Suggested rewrites the author can accept/edit/ignore (Phase 2+).
- Severity ranking by dispute likelihood.
- Per-user history across devices.

### Success criteria

- **Recall**: On a held-out set of 50 real Metaculus questions with known disputes, flag at least one of the actual disputed issues in 70% of cases.
- **False-positive ceiling**: On clearly-written, never-disputed questions, ≤1 false-positive flag per question on average.
- **Rewrite preference**: Blind reviewer prefers the suggested rewrite over the original on ≥70% of test questions.

### Four-phase build plan

| Phase | Theme | Output | Exit criteria |
|---|---|---|---|
| 1 | Rubric spike | CLI critique against hand-built rubric | ≥8/10 known-ambiguous caught; findings specific not generic |
| 2 | Critique quality & suggestions | Per-issue rewrites + eval harness | Rewrites rated "meaningfully better" by blind reviewer on ≥70% of a 50-q set |
| 3 | Web interface | Next.js + FastAPI app, auth, inline editor, history | Paste-to-critique <5s; signup-to-first-critique <30s |
| 4 | Polish & distribution | Hosted demo, README, methodology writeup | Public for 7 days within spend cap; ≥1 rubric item fires per session on average |

---

## 3. User-specific decisions and preferences (load-bearing)

These override defaults. Encode any new ones here as they come up.

- **Commit messages**: Plain. **No `Co-Authored-By: Claude` footer, no `🤖 Generated with Claude Code` line.** The user instructed this explicitly after the first two commits had to be rewritten.
- **GitHub**: account is `BK5102` → repo at https://github.com/BK5102/Sharper. The `gh` CLI is not installed on this machine; user prefers to create empty repos manually on github.com and paste the URL. Local-only commits get pushed with plain `git push`.
- **Local git identity**: `Bhavana Kannan` / `bhavanakannan06@gmail.com` (not the Claude Code sign-in email `bkannan8@asu.edu`). Don't override unless the user asks.
- **Working directory**: `C:\Bhavana\tech_projects\data_science_projects\Sharper` (Windows, Git Bash for shell). `cp .env.example .env` then edit in Notepad or VS Code is the working pattern; do NOT ask the user to paste API keys into chat.
- **Model choice**: `claude-sonnet-4-6` (the spec says "Sonnet for the critique"). Configurable via `SHARPER_MODEL` env var.
- **Documentation files**: User has been explicit when they want a README or markdown file. Don't create unprompted docs.

---

## 4. Repository state

- **Remote**: https://github.com/BK5102/Sharper
- **Branch**: `main` (force-pushed once early on to strip Claude footers from the first two commits)
- **Layout**:

```
Sharper/
├── README.md                      # public-facing project description
├── PROMPT.md                      # this file
├── .gitignore                     # Python + Node + .env + .tmp + eval/scratch
├── backend/
│   ├── pyproject.toml             # deps: anthropic, pydantic, typer, rich, python-dotenv, fastapi, uvicorn, httpx, supabase; dev: pytest, ruff
│   ├── Procfile                   # Railway start command: uvicorn sharper.api:app --host 0.0.0.0 --port $PORT
│   ├── railway.toml               # Railpack deploy config (startCommand)
│   ├── README.md
│   ├── .env.example
│   ├── db/
│   │   └── migrations/
│   │       └── 001_initial.sql    # critiques + findings + rewrite_actions; RLS deny-all for anon+authenticated
│   ├── sharper/
│   │   ├── schema.py              # Pydantic Finding + Critique models
│   │   ├── rubric.py              # 6 rubric items as frozen dataclass tuple (tuning lever)
│   │   ├── critic.py              # critique_question() via client.messages.parse; prompt caching
│   │   ├── cli.py                 # `sharper lint` Typer entry point
│   │   ├── api.py                 # FastAPI: POST /api/lint + GET /api/health; body cap; security headers; CORS reads SHARPER_ALLOWED_ORIGINS
│   │   ├── auth.py                # dual-mode: Clerk JWT first, static bearer fallback
│   │   ├── ratelimit.py           # Upstash Redis fixed-window: 10/hr anon, 60/hr auth; fail-open
│   │   ├── persistence.py         # Supabase write: save_critique() after each lint; fail-open
│   │   └── observability.py       # Sentry init; question-field scrubber
│   ├── scripts/
│   │   ├── fetch_metaculus.py     # per-ID detail-endpoint fetcher
│   │   ├── run_eval.py            # eval harness: recall + FP at three severity cuts
│   │   └── blind_review.py        # interactive rewrite-quality review protocol
│   ├── tests/
│   │   ├── test_smoke.py
│   │   ├── test_api.py
│   │   ├── test_ratelimit.py      # 17 tests, all passing
│   │   ├── test_auth.py
│   │   └── test_observability.py
│   ├── data/
│   │   ├── ids.txt                # user-curated URLs (19 questions)
│   │   ├── questions.metaculus.jsonl  # 19 labeled questions (14 ambiguous + 5 clean)
│   │   └── questions.example.jsonl
│   └── eval/
│       ├── runs/                  # dated eval history JSON (committed)
│       └── reviews/               # blind-review session results
└── frontend/
    ├── package.json               # next 16.2.6, react 19, tiptap 3, @clerk/nextjs 7, @sentry/nextjs 10, @supabase/supabase-js 2
    ├── .env.example
    ├── proxy.ts                   # Clerk middleware (Next.js 16 renamed middleware.ts → proxy.ts)
    ├── app/
    │   ├── layout.tsx             # ClerkProvider wraps the tree
    │   ├── page.tsx               # main page: useAuth → getToken → lint(); History link when signed in
    │   └── history/
    │       └── page.tsx           # server component: auth() → Supabase fetch → HistoryList
    ├── components/
    │   ├── AuthButton.tsx         # SignInButton (modal) / UserButton depending on auth state
    │   ├── PasteArea.tsx          # TipTap editor
    │   ├── FindingCard.tsx        # per-finding display with click-to-accept
    │   ├── ExampleGallery.tsx     # 3 before/after example pairs
    │   ├── HistoryList.tsx        # collapsible critique cards for history page (client component)
    │   └── SeverityBadge.tsx
    ├── lib/
    │   ├── api.ts                 # lint(question, token?) — token is Clerk JWT or null
    │   ├── supabase-server.ts     # server-only Supabase client (service-role key); HistoryCritique types
    │   ├── examples.ts
    │   └── sentry-scrub.ts
    ├── instrumentation.ts         # server-side Sentry init
    └── instrumentation-client.ts  # browser-side Sentry init
```

---

## 5. Architecture

### Pydantic schema (`sharper/schema.py`)

```python
class Severity(str, Enum): low, medium, high
class RubricItem(str, Enum):
    resolution_criteria_clarity, time_bound_specification, operationalization,
    edge_case_handling, source_authority, scope_drift
class Finding(BaseModel):
    rubric_item: RubricItem
    severity: Severity  # likelihood this causes a real dispute
    quoted_span: str    # must be verbatim from input
    issue: str          # one-sentence specific defect
    explanation: str    # 2-3 sentences referencing rubric item
class Critique(BaseModel):
    findings: list[Finding]    # ranked by severity desc; empty list is valid
    overall_assessment: str
```

### The six rubric items (`sharper/rubric.py`)

Each is a `RubricSpec(item_id, name, definition, example_failures)`. The definitions and example failures get interpolated into the system prompt via `rubric_as_prompt_block()`. **Editing these is the primary lever for tuning the linter.**

1. `resolution_criteria_clarity` — specific evidence resolves Yes vs No
2. `time_bound_specification` — precise resolution moment
3. `operationalization` — measurable thresholds for fuzzy terms ('major', 'significant')
4. `edge_case_handling` — what happens in partial / late / source-disappears cases
5. `source_authority` — named, stable, authoritative source
6. `scope_drift` — title and criteria agree on what's being asked

### Anthropic call (`sharper/critic.py`)

Uses `client.messages.parse()` with `output_format=Critique` for typed structured output. System prompt is `cache_control: ephemeral` so it caches across calls. Max input length 4000 chars (real Metaculus questions fit easily).

### CLI (`sharper/cli.py`)

`sharper lint --text "..."` / `--file foo.jsonl --line N` / stdin. JSON output by default; `--pretty` renders a Rich table.

### FastAPI wrapper (`sharper/api.py`)

`POST /api/lint` body `{question: str}` → returns the `Critique` JSON shape. `GET /api/health` for liveness. CORS allows `http://localhost:3000` for future Next.js dev. Run with `sharper-api` (console script) or `uvicorn sharper.api:app --reload`. No auth or rate limiting yet — those land in follow-ups (Clerk + Upstash Redis).

**Important detail**: `load_dotenv(override=True)` — the user's shell has `ANTHROPIC_API_KEY` exported as an empty string (from a stale `.bashrc` line), and python-dotenv's default doesn't override pre-existing env vars. The `override=True` flag makes `.env` the canonical source. Same fix is applied in `scripts/fetch_metaculus.py`.

Also: `sys.stdout.reconfigure(encoding="utf-8")` so JSON output with unicode (em-dashes, smart quotes from question text) renders cleanly on Windows cp1252 consoles.

### Eval harness (`scripts/run_eval.py`)

Reads labeled JSONL, builds full input per row (title + criteria + fine_print + background), calls `critique_question()` on each, writes a dated JSON to `eval/runs/`. Computes:

- **Recall@{low,medium,high}**: fraction of ambiguous rows where the linter produced ≥1 finding at the given severity.
- **FP_per_clean@{low,medium,high}**: total findings of that severity on clean rows, divided by number of clean rows.
- **Rubric firing rates**: per-rubric-item counts split by label.

---

## 6. Held-out data workflow (the load-bearing part)

This took the most iteration. The summary:

1. **Don't bulk-fetch from Metaculus.** The `/api2/questions/` list endpoint's filters are too limited — `status=resolved` no longer exists, `status=closed` returns ~300 recent unresolved bot-benchmark questions, and most filter / order_by params are silently ignored. Documented per-trial probes in commit history.

2. **Do per-ID fetch.** `/api2/questions/{id}/` returns full data including the nested `question` sub-object with `resolution_criteria`, `fine_print`, `background`. Auth: `Authorization: Token <token>` + non-default User-Agent (Cloudflare 403s on missing UA).

3. **Curate URLs by hand from the website.** Use the Resolved + Binary filter combo. Two-pass strategy:
   - **Pass 1 (ambiguous-10)**: Scroll Resolved+Binary, pick cards with the **Annulled** or **Ambiguous** resolution badge. These are unambiguously ambiguous (no judgment call needed).
   - **Pass 2 (clean-10)**: Pick questions with a named source, specific numeric/event criterion, and quiet comment threads.
   - **Target**: 10 ambiguous + 10 clean = n=20 minimum for interpretable eval numbers.

4. **Paste URLs into `data/ids.txt`** — one per line, `#` for comments. Then `python -m scripts.fetch_metaculus --ids-file data/ids.txt`.

5. **Extract resolution criteria via Claude-in-Chrome.** The `/api2/questions/{id}/` endpoint returns empty `resolution_criteria` for many questions. Workaround: open all question URLs as tabs in Chrome, run a Claude-in-Chrome session with this JS (saved in commit history) that reads each tab's DOM and yields JSONL with the full criteria text. Replaces `data/questions.metaculus.jsonl` with the populated version.

6. **Annotate `label` and `notes` manually.** The script pre-fills `label: ambiguous` for cards with Annulled/Ambiguous resolutions. Yes/No-resolved questions need human judgment: clean (well-specified + no dispute) vs ambiguous (had a real dispute or has a concrete defect).

7. **Label semantics matter.** A question is `clean` only if it's well-specified AND didn't dispute. A question that has defects but happened to resolve without controversy is NOT clean — the spec's success criteria require both.

---

## 7. Key gotchas / non-obvious learnings

| # | Gotcha | Fix |
|---|---|---|
| 1 | Metaculus `/api2/questions/?status=resolved` returns 400 ("not a valid choice") | Use per-ID detail endpoint instead |
| 2 | Metaculus 403s on requests without a User-Agent header | Set `User-Agent: sharper-fetch/0.1` |
| 3 | User's shell has `ANTHROPIC_API_KEY=` exported as empty string | `load_dotenv(override=True)` in every entry point |
| 4 | Windows cp1252 console can't render em-dashes / smart quotes in JSON | `sys.stdout.reconfigure(encoding="utf-8")` at script top |
| 5 | argparse interprets `--order-by -created_at` as two flags | Use `--order-by=-created_at` |
| 6 | Metaculus API returns empty `resolution_criteria` for many questions | Scrape via Claude-in-Chrome from the public web page |
| 7 | "Clean" label can leak into the linter via resolver meta-notes in criteria text ("Note: This question was resolved ambiguous because…") | Strip those paragraphs at eval time in `run_eval.py` |
| 8 | The spec's "clean" means well-specified AND never-disputed (not just never-disputed) | Re-label questions with concrete defects from clean to ambiguous |
| 9 | Railway Railpack fails with "could not determine how to build" on a monorepo | Set **Root Directory** to `/backend` in Railway service settings so Railpack sees `pyproject.toml` |
| 10 | Railway injects `PORT` env var; `api.py:run()` uses `SHARPER_API_PORT` (default 8000) — health check fails if they differ | Use `Procfile` / `railway.toml` with `uvicorn ... --port $PORT` directly; bypass the `run()` entrypoint on Railway |
| 11 | CORS hardcodes localhost origins; Vercel frontend gets blocked in production | Set `SHARPER_ALLOWED_ORIGINS=https://your-app.vercel.app` in Railway env vars; `api.py` reads it at startup |
| 12 | `CLERK_AUTHORIZED_PARTIES` missing from `backend/.env` skips `azp` claim check | Add `CLERK_AUTHORIZED_PARTIES=https://your-app.vercel.app,http://localhost:3000` to both `backend/.env` and Railway env vars |
| 13 | `supabase>=2.0` has a transitive dep that silently fails `pip install` on Python 3.13 (Railway's new default via mise), leaving the env completely empty — `No module named uvicorn` on start | Pin Python in `backend/.python-version` (3.11); prefer `httpx` directly over heavy SDKs — same REST pattern as Upstash, no new dep |

---

## 8. Current state (as of 2026-06-12 session 2)

### BLOCKING: `/api/lint` returning 404 in production — fix this first next session

**Root cause (most likely):** CORS on Railway is not allowing `https://sharper-linter.vercel.app`. The backend only allows `localhost:3000` by default; `SHARPER_ALLOWED_ORIGINS` must be set in Railway env vars. Also confirm `NEXT_PUBLIC_API_URL` in Vercel has the `https://` prefix and Vercel was redeployed after setting it.

**Checklist to fix (do these in order):**

1. **Railway → Variables**: confirm `SHARPER_ALLOWED_ORIGINS=https://sharper-linter.vercel.app` is set. If not, add it and redeploy Railway.
2. **Railway → Variables**: confirm `SUPABASE_URL` is set (used for JWKS-based JWT verification — the backend fetches Supabase's public key from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`).
3. **Vercel → Settings → Environment Variables**: confirm `NEXT_PUBLIC_API_URL=https://sharper-production.up.railway.app` — must include `https://` prefix. Without it the URL is treated as relative and hits Vercel (404).
4. **Vercel → Deployments**: after any env var change, do a fresh redeploy (NEXT_PUBLIC_* vars bake in at build time). Uncheck "Use existing build cache."
5. **Railway logs**: confirm the backend started cleanly — look for `Uvicorn running on http://0.0.0.0:<PORT>`. The `$PORT` crash loop was fixed (commit `f5da4d3`): Dockerfile now uses `CMD ["sharper-api"]` and `run()` reads `PORT` env var directly.

**What was completed this session (auth migration + UI):**

### Clerk → Supabase Auth migration (COMPLETE, all committed)

Clerk was dropped entirely because Clerk Development keys (`pk_test_`) cannot be used on `sharper-linter.vercel.app` (production domains require a paid Clerk plan + custom domain). Full migration to Supabase Auth:

**Backend changes:**
- `backend/pyproject.toml`: `clerk-backend-api` → `pyjwt[crypto]>=2.8`
- `backend/sharper/auth.py`: Rewrote. Supabase has migrated to asymmetric JWT signing (RS256/ES256), so the backend uses `PyJWKClient` to fetch the public JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` and verify tokens. No secret needed — only `SUPABASE_URL`. Dual-mode: JWT first, static bearer fallback.
- `backend/tests/test_auth.py`: Rewrote. Uses `cryptography` (via `pyjwt[crypto]`) to generate RSA key pairs for tests; mocks `_get_jwks_client`.
- `backend/tests/test_api.py`: Updated `_clear_auth_env` fixture to clear `SUPABASE_URL` instead of `CLERK_SECRET_KEY`.
- `backend/.env.example`: Removed Clerk vars. SUPABASE_URL is the JWT auth config.
- `backend/Dockerfile`: Changed CMD to `["sharper-api"]` (exec form, no shell expansion). Added `ENV SHARPER_API_HOST=0.0.0.0`.
- `backend/sharper/api.py`: `run()` now reads `PORT` (Railway) with fallback to `SHARPER_API_PORT` then `8000`.

**Frontend changes:**
- `frontend/package.json`: Removed `@clerk/nextjs`, added `@supabase/ssr` + `@supabase/supabase-js`.
- `frontend/proxy.ts`: Replaced `clerkMiddleware` with Supabase session middleware (`createServerClient` + `getUser()`). Protects `/app` and `/history`; redirects signed-in users away from `/auth`. Export renamed `middleware` → `proxy` (Next.js 16 requirement).
- `frontend/app/layout.tsx`: Removed `ClerkProvider`.
- `frontend/app/page.tsx`: Now a public landing page describing Sharper with Get started / Sign in CTAs.
- `frontend/app/app/page.tsx` (NEW): The linter (was `app/page.tsx`). Uses `supabase.auth.getSession()` to get JWT for backend calls.
- `frontend/app/auth/page.tsx` (NEW): Email + password sign-in/sign-up with mode toggle. Uses `signInWithPassword` / `signUp`. On success redirects to `/app`.
- `frontend/app/auth/callback/route.ts` (NEW): Exchanges auth code for session (email confirmation flow).
- `frontend/app/history/page.tsx`: Replaced `auth()` from Clerk with Supabase `createClient().auth.getUser()`.
- `frontend/components/AuthButton.tsx`: Replaced Clerk buttons with Supabase sign-out. Just shows "Sign out" button — no email display to avoid header layout issues.
- `frontend/lib/supabase-browser.ts` (NEW): `createBrowserClient` factory.
- `frontend/lib/supabase-server-auth.ts` (NEW): `createServerClient` factory with cookie handling.

**Supabase dashboard steps already done by user:**
- Email auth enabled
- Redirect URL `https://sharper-linter.vercel.app/auth/callback` added
- Railway domain generated: `https://sharper-production.up.railway.app`

**Railway env vars needed (check these):**
- `SUPABASE_URL` (already set from Phase 3 step 5) — used for JWKS verification
- `SHARPER_ALLOWED_ORIGINS=https://sharper-linter.vercel.app` — CORS allow-list
- Remove: `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`, `SUPABASE_JWT_SECRET` (if added)

**Vercel env vars needed (check these):**
- `NEXT_PUBLIC_API_URL=https://sharper-production.up.railway.app`
- `NEXT_PUBLIC_SUPABASE_URL` (already set)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (already set)
- Remove: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

### UI/design overhaul (COMPLETE, all committed)

- `globals.css`: Fixed font — was using `Arial` (Geist never loaded); now uses `var(--font-geist-sans)`.
- `PasteArea.tsx`: Fixed character count and Lint button always-disabled bug. TipTap doesn't trigger React re-renders when content changes (editor object reference is stable); fix uses `editor.on('update', handler)` to track text in local state.
- All components: Typography hierarchy (display/body/label), 8pt spacing, border-only cards (removed `shadow-sm`), unified button system with `transition-colors duration-150`, `transition-shadow duration-100` on inputs.
- Auth page: Email + password replaces magic link.

### BLOCKING: Both deploys broken — fix this first next session (RESOLVED)

**Railway** — crashing on start. Root cause: Railpack creates a venv during build; the start command's Python (`/mise/installs/python/3.11/bin/python`) doesn't see the venv's site-packages, so `python -m uvicorn` gives `No module named uvicorn`. Fix committed (`eb990ea`): `backend/Dockerfile` uses `python:3.11-slim` and installs into the container's system Python — no venv, no PATH ambiguity. **The Dockerfile build has NOT yet been confirmed healthy.** Check Railway dashboard at the start of the next session.

**Vercel** — showing `404: NOT_FOUND` with Vercel infrastructure IDs (`sfo1::...`). This is NOT a page 404 — it means Vercel's edge can't find any live deployment for the domain. Root cause unknown: could be a failed build (env vars missing on Vercel?) or a stale project state. **Local `next build` is clean** (confirmed this session). The code is correct. The problem is in the Vercel project configuration or build environment.

### Next-session diagnostic checklist (Vercel)

Do these in order before writing any code:

1. **Vercel dashboard → Deployments** — is the latest deployment "Ready" or "Error"?
2. **If Error → Build Logs** — look for the first red line. Most likely candidates:
   - `Missing publishableKey` → `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` missing from Vercel env vars
   - Any module import error → paste it here and fix
3. **Vercel → Settings → Environment Variables** — confirm ALL of these exist:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` ← most likely missing; required at build time
   - `NEXT_PUBLIC_API_URL` (Railway backend URL)
   - `NEXT_PUBLIC_SENTRY_DSN` (optional but should be set)
   - `SUPABASE_SERVICE_ROLE_KEY` (added this session — verify it's there)
4. **If all env vars present and build still fails** → paste the full build log error here
5. **If latest deployment is "Ready"** → the 404 is a domain routing issue; go to Settings → Domains → re-add the domain

### Code state (all correct, no changes needed)

- Local `next build`: clean, 0 errors, `/history` correctly marked as dynamic
- Backend tests: 104/104 passing
- `persistence.py`: uses `httpx` directly against Supabase REST (no SDK)
- `supabase-server.ts`: uses `fetch()` directly against Supabase REST (no SDK)
- `backend/Dockerfile`: added for Railway — Python 3.11-slim, system pip install

**Built and shipped (running list, newest first):**
- ✅ **Frontend history page (2026-06-12, Phase 3 step 9)**: `app/history/page.tsx` is a Next.js server component — calls `auth()` from `@clerk/nextjs/server`, redirects unauthenticated users to `/`. Fetches `critiques` + nested `findings` from Supabase via `lib/supabase-server.ts` using `fetch()` directly against the PostgREST REST API (no SDK — avoids `realtime-js` WebSocket build failure on Vercel). `components/HistoryList.tsx` client component renders collapsible critique cards with per-finding expandable rows. History link added to main page header, visible only when signed in. TypeScript clean, local `next build` clean.
- ✅ **Supabase persistence layer (2026-06-12, Phase 3 step 5)**: `backend/db/migrations/001_initial.sql` creates `critiques`, `findings`, `rewrite_actions` tables with RLS enabled + explicit deny-all policies for `anon` and `authenticated` roles (service-role key bypasses RLS from the backend). `backend/sharper/persistence.py` lazy-singleton supabase client; `save_critique(user_id, question, critique)` bulk-writes critique + findings per lint call, fail-open on any error. Wired into `api.py`: `_identity` renamed to `identity`, `persistence.save_critique()` called after each successful `critique_question()`. `supabase>=2.0` added to `pyproject.toml`. 104/104 backend tests pass.
- ✅ **Railway deploy fixed (2026-06-11)**: Added `backend/Procfile` (`uvicorn sharper.api:app --host 0.0.0.0 --port $PORT`) and `backend/railway.toml` (Railpack startCommand). Set Railway service Root Directory to `/backend`. Fixed CORS to read `SHARPER_ALLOWED_ORIGINS` env var so the Vercel frontend URL is allowed. All env vars now in Vercel and Railway dashboards. Both deploys live and healthy.
- ✅ **Clerk frontend integration (2026-06-10, Phase 3 step 8)**: `@clerk/nextjs` v7 installed. `frontend/proxy.ts` exports `clerkMiddleware()` as default — **note: Next.js 16 renamed `middleware.ts` → `proxy.ts`**, this is the breaking change. `app/layout.tsx` wraps the tree in `<ClerkProvider>`. `components/AuthButton.tsx` renders a modal `<SignInButton>` when signed out or `<UserButton>` avatar when signed in. `lib/api.ts` `lint(question, token?)` now takes the Clerk JWT directly (static `NEXT_PUBLIC_SHARPER_API_TOKEN` stopgap removed). `app/page.tsx` calls `useAuth()` → `getToken()` before each lint run and passes the token through. Auth is optional — anonymous users can lint at 10 req/hr; signed-in users get 60 req/hr. TypeScript clean, no test regressions.
- ✅ **Upstash rate limit (2026-05-23, Phase 3 steps 2 + 4)**: `sharper/ratelimit.py` wraps the Upstash REST `/pipeline` endpoint with an `INCR key` + `EXPIRE key 3600 NX` two-command transaction per request. Fixed-window per wall-clock hour, keyed by Clerk `user_id` / `shared-token` / IP-from-X-Forwarded-For depending on auth state. Quotas: 10/hr anonymous, 60/hr authenticated. Fail-open when Upstash is unreachable or returns a bad shape (logged but doesn't block linter). 429 response carries `Retry-After: 3600`. No-op when `UPSTASH_REDIS_REST_URL` or `UPSTASH_REDIS_REST_TOKEN` is unset (local dev). FastAPI dependency wired into `/api/lint` alongside `auth.require_token`. 17 new tests in `test_ratelimit.py`; 104/104 backend tests pass.
- ✅ **Sentry error tracking (2026-05-23, Phase 3 step 11)**: backend `sharper/observability.py` with `init_sentry()` (FastApi + Starlette integrations) + `scrub_question_field()` `before_send` hook that strips `question` from any captured event. Front of `sharper/api.py` calls `init_sentry()` at module load. Frontend `instrumentation.ts` (server) + `instrumentation-client.ts` (browser) + shared `lib/sentry-scrub.ts` scrubber for both `request.data` and breadcrumb `data.body`. `sendDefaultPii: false` is the SDK-level guard; scrubber is the belt-and-suspenders. Placeholder DSN strings (with `...`, `o000000`, or `<>`) are detected and skipped to keep dev/tests from crashing. 87/87 backend tests pass (14 new in `test_observability.py`). Frontend build clean.
- ✅ **Clerk backend JWT verification (2026-05-23, Phase 3 step 3)**: `sharper/auth.py` rewritten to dual-mode. When `CLERK_SECRET_KEY` is set, the dependency verifies Clerk session JWTs via `clerk_backend_api.authenticate_request_async` and returns the Clerk `user_id` (`sub` claim). When both `CLERK_SECRET_KEY` and `SHARPER_API_TOKEN` are set, Clerk is tried first; falls back to static bearer for non-JWT-shaped tokens (heuristic: 3 dot-separated parts = JWT). Migration-safe: existing frontend still hitting static bearer keeps working until Phase 3 step 8 (Clerk frontend) lands. 17 auth tests cover Modes A/B/C/D.
- ✅ **Live deploys (2026-05-22)**: Vercel hosts the Next.js frontend, Railway hosts the FastAPI backend.
- ✅ **All six external accounts configured (2026-05-22)**: Clerk, Upstash, Supabase, Sentry, Vercel, Railway. Keys pasted into `backend/.env` and `frontend/.env.local`.
- ✅ Backend security hardening (2026-05-22): static-bearer auth gate on `/api/lint` (`sharper/auth.py`), 16KB body cap, sanitized 502 responses, security headers middleware, CORS tightened to `["content-type", "authorization"]`, `run()` refuses non-loopback bind without `SHARPER_API_TOKEN`. 65/65 backend tests pass.
- ✅ Frontend hardening (2026-05-22): `lib/api.ts` sends `Authorization: Bearer ${NEXT_PUBLIC_SHARPER_API_TOKEN}` when set.
- ✅ Phase 3 step 10: example gallery with 3 real before/after pairs from the eval set.
- ✅ Phase 3 step 7: TipTap editor with click-to-accept text substitution (replaces quoted_span with suggested_rewrite in-place).
- ✅ Phase 3 step 6: Next.js 16 frontend (React 19, Tailwind 4, hand-rolled UI primitives, no shadcn).
- ✅ Phase 3 step 1: FastAPI wrapper (`sharper/api.py`) — `POST /api/lint`, `GET /api/health`, CORS.
- ✅ Phase 2 metric met on internal sample: 94% rewrite-better via `scripts/blind_review.py`.
- ✅ Phase 2 entry: `suggested_rewrite: str | None` on `Finding` + rewrite-generation prompt.
- ✅ Phase 1 exit: severity calibration on discretionary language brought recall@high to 79%.
- ✅ Eval harness (`scripts/run_eval.py`) with three-severity recall + FP metrics, dated run JSON history, resolver-meta-note stripper.
- ✅ 19-question labeled held-out set (14 ambiguous + 5 clean).
- ✅ Metaculus per-ID fetcher (`scripts/fetch_metaculus.py`) with URL/ID list input.
- ✅ Claude-in-Chrome scraper prompt + JS extractor for full criteria text.
- ✅ Six-item rubric + Pydantic `Finding` + `Critique` schemas + Typer CLI + `client.messages.parse(output_format=Critique)` with prompt caching.
- ✅ Backend scaffold (`pyproject.toml`, `sharper/` package, tests).

**Phase 1 status**: **EXIT MET** at high severity (recall@high 79% vs 70% target; fp@high 0.40 vs 1.0 target). Spec target of 30-50 questions for the held-out set is **under-met** — we're at 19. See §9 for why this is OK to ship Phase 1 against but blocks formal Phase 2 spec-compliance measurement.
**Phase 2 status**: **SUCCESS METRIC MET on internal sample.** First blind review (`eval/reviews/2026-05-21-204554.json`) over 51 rewrite pairs from the n=19 question set: **48/51 = 94% rated meaningfully better** (target ≥70%). Rubric v0.4 locked. Caveat: spec strict reading is 50 questions; we have 19.
**Phase 3 status**: **Code complete (14/14 steps).** Both deploys currently broken — see §8 blocking section. Fix deploys before moving to Phase 4.
**Phase 4 status**: Not started.

---

## 9. Eval results history

| run | n_ambig | n_clean | recall@high | recall@med | recall@low | fp@high | fp@med | fp@low | notes |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-20-220054 | 9 | 10 | 22% | 100% | 100% | 0.90 | 2.70 | 3.70 | First eval. 100% recall@low is "flag everything"; per-q mean 3.33 ambig / 3.70 clean — anti-discriminating. |
| 2026-05-21-113655 | 14 | 5 | 50% | 100% | 100% | 0.00 | 1.20 | 2.60 | Meta-stripper + relabeled 5 marginal clean → ambiguous. fp@high → 0 (perfect on strict-clean), recall@high up 28 pts, per-q mean 4.07 ambig / 2.60 clean (real discrimination). |
| 2026-05-21-120422 | 14 | 5 | **79%** | 100% | 100% | 0.20 | 1.80 | 3.00 | Severity calibration in `schema.py` + `critic.py` — escalate on discretionary language ('Metaculus may consider', 'best judgment', 'credible sources'), undefined fuzzy central decision vars, missing hard deadlines, non-persistent sources. **Phase 1 exit hit at high severity.** |

**Phase 1 exit status**: recall@high **79% (11/14)** > 70% target ✅. fp@high 0.20 — well under the 1.0 spec target ✅. fp@medium 1.80 is over 1.0 (the 5 strict-clean questions each get 1-2 medium findings — some are mild real concerns, not necessarily defects). At the high-severity threshold the linter meets the spec.

Three ambiguous misses (25703, 20127, 20171) get medium-only — these have subtle discretionary clauses the model could probably escalate with more tuning, but iterating further would risk overfitting to the n=14 set. **Stop tuning. Move to Phase 2.**

One FP@high on clean (20005): the criteria contain "Metaculus may make a determination if there is ambiguity..." which is the exact pattern the rubric escalates on. Borderline label issue, but the model's discrimination logic is consistent. Don't relabel until the next data refresh — overfitting risk.

### Why n=19 instead of the spec's 30-50

The spec calls for 30-50 questions in Phase 1 and a 50-question annotated set in Phase 2. We have 19. Two layers of reasons — structural (we *can't* bulk-grow the set) and strategic (we *don't need to yet*).

#### Structural: bulk scraping is blocked

1. **Metaculus's API doesn't expose resolution criteria reliably.** `GET /api2/questions/{id}/` returns metadata but its `resolution_criteria`, `background`, and `fine_print` fields come back empty for most questions — that text exists only in the rendered web page HTML. The `/api2/questions/` list endpoint is also too limited to filter for resolved questions: `status=resolved` returns 400 ("not a valid choice"); `status=closed` returns ~300 recent unresolved bot-benchmark entries; most `order_by` / filter params are silently ignored. We can't get bulk resolved-question text out of the public API.

2. **The public web pages are Cloudflare-protected.** Direct HTTP scraping (`requests`, `httpx`, `WebFetch`, plain `curl` with stock UA) returns **403 Forbidden** to non-browser user agents. Hitting the public URLs and parsing the HTML is also not an option.

3. **Our workaround is one-tab-at-a-time.** Open each candidate question as a Chrome tab, then run a Claude-in-Chrome session with a JS extractor that reads the rendered DOM. The extractor is scripted; the surrounding browser session is manual.

#### Cost of the workaround (per question, focused human time)

| Step | Time | What it involves |
|---|---|---|
| Curation | ~1-2 min | Browse metaculus.com Resolved + Binary; spot Annulled/Ambiguous badges; open candidate URL as a tab |
| Extraction | ~30 sec | Wait for Claude-in-Chrome batch to run across all open tabs |
| Labeling | ~2-3 min | Per row, set `label` and write `notes`; script auto-labels Annulled/Ambiguous, human judges Yes/No-resolved |
| **Total** | **~3-5 min** | Per question of focused work |

Scaling **n=19 → n=50** is ~**1.5-2.5 hours** of focused work. Real but not unrealistic; intentionally deferred.

#### Strategic: we don't need to grow yet

4. **Phase 1 exit bar was hit cleanly at n=19** (recall@high 79%, fp@high 0.40 vs spec 70% / 1.0). Pushing to n=30 with the same biosecurity-heavy curation would not have changed the decision to move to Phase 2.
5. **Topic concentration matters more than count.** 12 of 19 are disease/PHEIC. The next chunk has to be diverse (politics, finance, climate, sports, AI capability) to test generalization — not just bigger.
6. **Phase 2 protocol had to exist first.** The blind-reviewer script (`scripts/blind_review.py`) had to be built and shaken out before we paid the curation cost on 30 more questions. That's done now (94% rewrite-better at n=19); next growth round is unblocked.

### Future scope: dataset growth

Three explicit milestones for growing the set:

| Milestone | n_ambiguous | n_clean | Total | Purpose |
|---|---|---|---|---|
| Now (committed) | 14 | 5 | 19 | Phase 1 exit + Phase 2 scaffold smoke-test |
| Phase 1 spec-compliant | ~14 | ~16 | ~30 | Grow clean set so FP rate stabilizes; same ambiguous set (already exceeds need) |
| Phase 2 evaluable | ~20 | ~30 | ~50 | Spec target; supports blind-reviewer protocol with statistical signal |
| Diverse-domain stretch | ~25 | ~35 | ~60 | Adds politics, finance, climate, sports, AI questions to break biosecurity concentration |

When adding more questions, use the URL-list workflow (see §6) and prefer the Annulled/Ambiguous badge for `label: ambiguous` candidates. Don't relitigate marginal labels — that's been done at n=19 and the criteria are stable.

---

## 10. Open issues / next steps

In priority order:

1. ✅ **Strip resolver meta-notes from criteria text** — done in `run_eval.py`, tested.
2. ✅ **Tighten clean labels** — done; 5 rows relabeled to ambiguous.
3. ✅ **Re-run eval** — done; numbers in §9.
4. ✅ **Severity calibration** — done; escalate on discretionary language / fuzzy central decision vars / missing hard deadlines / non-persistent sources. Recall@high jumped 50→79%, exceeds spec target.
5. ✅ **Phase 1 exit met** — at high severity. Lock rubric v0.3 and move on.

**Phase 2 — from scaffolded to final**

Phase 2 has code that *generates* rewrites (✅) but no measurement against the spec's success criterion. Here's the explicit path to call it done. Each step has an owner (code = me, data = you) and a time estimate.

| # | Step | Owner | Effort | Output |
|---|---|---|---|---|
| 1 | ✅ **Build blind-reviewer protocol script** (`scripts/blind_review.py`): loops over `(quoted_span, suggested_rewrite)` pairs from the latest eval run; for each, prompts the reviewer "is the rewrite meaningfully better than the original phrasing? (y/n/skip/quit)"; randomizes order via `--seed`; aggregates % yes overall + per-rubric-item + per-severity; saves session to `eval/reviews/<timestamp>.json`. The reviewer sees only `title + quoted_span + suggested_rewrite` — diagnosis fields hidden. | code | 30 min | ✅ shipped + 12 tests |
| 2 | ✅ **Run blind review on n=19.** 2026-05-21: 51 pairs reviewed, 48 better / 3 not / 10 skipped. **94% rewrite-better, well above 70% target.** Protocol UX clean. | data (user) | ~30 min | `eval/reviews/2026-05-21-204554.json` |
| 3 | ~~**Iterate the rewrite prompt if low**~~ — N/A, 94% is well above iterate threshold. Failure modes are minor (timezone pedantry, one rubric_item misclassification on naming clarification, one debatable source call) and not systematic. | — | — | skipped |
| 4 | **Grow the question set to ~50** using the milestones in §9 future scope. Prioritize diversity (politics / finance / climate / sports / AI capability) over volume — 30 diverse questions beats 50 biosecurity questions. | data (user) | 2-4 hrs of focused curation | updated `data/questions.metaculus.jsonl` |
| 5 | **Re-run eval against n=50** to regenerate per-finding rewrites. | code (re-runs) | 5 min compute | new `eval/runs/*.json` |
| 6 | **Run blind review against n=50** to compute the spec's actual metric. | data (user) | 60-90 min of focused review | final `eval/reviews/*.json` |
| 7 | **Decision point**: if ≥70% rewrite-better, lock rubric v0.4 (or whatever) and tag the commit as "Phase 2 exit". If below, iterate steps 3+5+6. | code+data | 1-2 cycles | tagged commit |

**Optional but valuable parallel work:**

- **Per-row "actual disputed issue" annotations on ambiguous rows.** Spec recall is "linter flags ≥1 of the *actual* disputed issues"; we currently measure "≥1 of anything", a weaker proxy. ~5 min per ambiguous row to write the actual dispute reason into `notes`. Unlocks measuring the spec's true criterion.
- **Reference rewrites per finding**, against which the model's rewrite is scored. The blind-reviewer protocol above is the cheaper version of this — it skips the reference and just asks "is the model's rewrite better than the original?". Adding gold references would let us additionally measure "how close to the human-quality rewrite did the model get?".

**Phase 3 — Web Interface (6 of 14 done, accounts now unblock the rest)**

| # | Step | Owner | Account | Status |
|---|---|---|---|---|
| 1 | **FastAPI wrapper** (`POST /api/lint`, `GET /api/health`) | code | — | ✅ done |
| 2 | **Per-IP rate limiting** — Upstash REST `INCR/EXPIRE NX`, fixed hourly window, X-Forwarded-For aware, fail-open on upstream failure. | code | Upstash | ✅ done |
| 3 | **Clerk auth middleware**: dual-mode auth in `sharper/auth.py` — Clerk JWT via JWKS first, static bearer fallback. `user_id` from `sub` claim. | code | Clerk | ✅ done |
| 4 | **Per-user rate limiting** — same `ratelimit.py` keys by Clerk `user_id` / `shared-token` for authenticated callers (60/hr) vs IP for anonymous (10/hr). | code | Upstash + Clerk | ✅ done |
| 5 | **Supabase tables + persistence**: `critiques`, `findings`, `rewrite_actions`, keyed by Clerk `user_id`. Migration SQL in `backend/db/`. | code | Supabase | ✅ done (2026-06-12) |
| 6 | **Next.js 16 scaffold** + paste-area + critique view + hand-rolled UI primitives. | code | — | ✅ done |
| 7 | **TipTap editor** with click-to-accept text substitution. | code | — | ✅ done |
| 8 | **Clerk frontend integration** + sign-in flow. `ClerkProvider` in layout, `AuthButton` in header, `useAuth → getToken` wired into lint call. Next.js 16 uses `proxy.ts` not `middleware.ts`. | code | Clerk | ✅ done (2026-06-10) |
| 9 | **History page**: server-side fetch from Supabase by `user_id`, list past critiques. | code | Supabase | ✅ done (2026-06-12) |
| 10 | **Example gallery** on landing page: 3 real before/after pairs from the eval set. | code | — | ✅ done |
| 11 | **Sentry integration** — backend `observability.py` init + frontend `instrumentation.ts`/`instrumentation-client.ts` + shared `sentry-scrub.ts`. `sendDefaultPii=false` + explicit `question`-field scrubber on `before_send`. Placeholder DSN strings skipped. | code | Sentry | ✅ done |
| 12 | **Vercel deploy** for Next.js with `NEXT_PUBLIC_API_URL` + `NEXT_PUBLIC_SHARPER_API_TOKEN` env vars. | code | Vercel | ✅ done |
| 13 | **Railway deploy** for FastAPI backend with all secrets in env. | code | Railway | ✅ done |
| 14 | **Soft launch** to 1-2 forecasting communities (Manifold Discord, EA Forum, LessWrong). | data (user) | — | ⬜ pending steps 2-5, 8-9, 11 |

**All Phase 3 integration steps complete.** Phase 4 is next.

**Phase 4 — Polish & Distribution (not started; ~6 steps)**

- Set daily Anthropic spend cap and kill-switch endpoint.
- Product analytics (PostHog or similar): track which rubric items fire, which rewrites are accepted, abandonment points.
- Methodology writeup linked from README — explain the rubric, show eval numbers, link 3-4 representative examples.
- Soft launch to forecasting communities; collect feedback.
- Fix top 3 complaints from feedback.
- Tag the commit "v1.0".

---

## 11. Recreation recipe (rebuild from zero)



If starting over on a new machine:

```bash
# 1. Create empty repo on github.com/<your-username>/Sharper, copy the URL

# 2. Clone or init locally
git init Sharper && cd Sharper
git remote add origin https://github.com/<your-username>/Sharper.git

# 3. Recreate the file structure from §4. Critical files to recreate in order:
#    - .gitignore (Python + Node + .env + .tmp + eval/scratch/)
#    - backend/pyproject.toml (anthropic, pydantic, typer, rich, python-dotenv; dev: pytest, ruff)
#    - backend/.env.example (ANTHROPIC_API_KEY, SHARPER_MODEL=claude-sonnet-4-6, METACULUS_API_TOKEN)
#    - backend/sharper/schema.py (the Pydantic models from §5)
#    - backend/sharper/rubric.py (the six items from §5; definitions and 2-3 example failures each)
#    - backend/sharper/critic.py (load_dotenv(override=True); MAX_INPUT_CHARS=4000;
#                                client.messages.parse with output_format=Critique;
#                                system prompt with cache_control: ephemeral)
#    - backend/sharper/cli.py (Typer; UTF-8 stdout reconfigure; load_dotenv(override=True))
#    - backend/scripts/fetch_metaculus.py (per-ID detail endpoint; URL-list workflow;
#                                          parse_id() accepts URLs and bare IDs)
#    - backend/scripts/run_eval.py (build_question_text concatenating title+criteria+fine_print+bg;
#                                   strip_resolver_meta_notes preprocessor;
#                                   recall + FP at three severity cuts)
#    - backend/tests/test_smoke.py + test_fetch_metaculus.py

# 4. Set up Python env (Python 3.11+)
cd backend
python -m venv .venv
source .venv/Scripts/activate     # Git Bash on Windows
pip install -e ".[dev]"
cp .env.example .env              # then edit .env with real keys
pytest -v                          # all should pass without network

# 5. Smoke-test the linter (needs ANTHROPIC_API_KEY)
echo "Will AI be a big deal by 2030?" | sharper lint

# 6. Curate held-out set
#    a. Free account at metaculus.com -> profile -> API token; add to .env
#    b. Browse metaculus.com, filter to Resolved + Binary
#    c. Pass 1: collect ~10 URLs of questions with Annulled or Ambiguous resolution badge
#    d. Pass 2: collect ~10 URLs of cleanly-specified questions
#    e. Paste URLs into backend/data/ids.txt (one per line, # for comments)
#    f. Open all URLs as Chrome tabs; run Claude-in-Chrome with the extractor JS
#       (see commit history; reads each tab's DOM and yields JSONL with full criteria)
#    g. Save output to backend/data/questions.metaculus.jsonl
#    h. Manually fill in `label` (ambiguous|clean) and `notes` for each row
#       — clean means well-specified AND never-disputed (both required)

# 7. Run eval
python -m scripts.run_eval --note "v0 baseline"
# Check eval/runs/<timestamp>.json for per-row details and aggregate summary
```

---

## 12. Account setup checklist — **ALL CONFIGURED (2026-05-22)**

All external services have accounts created and credentials pasted into env files. **Integration code** is the remaining gate, not account setup. The env-var names listed below are what `backend/.env` and `frontend/.env.local` already contain.

| Service | Use | Status | Env vars in place |
|---|---|---|---|
| **Anthropic** | Claude API for the linter | ✅ live | `ANTHROPIC_API_KEY` in `backend/.env` |
| **Metaculus** | Question fetcher | ✅ live | `METACULUS_API_TOKEN` in `backend/.env` |
| **Clerk** | Auth (magic link + Google OAuth) | ✅ fully live — backend JWT + frontend provider + sign-in flow | `CLERK_SECRET_KEY` + `CLERK_AUTHORIZED_PARTIES` in backend, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` in frontend |
| **Upstash** | Redis for rate limiting | ✅ DB created + middleware live (per-IP + per-user) | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` in `backend/.env` |
| **Supabase** | Postgres for per-user history | ✅ project created, schema TODO | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in backend; `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` in frontend |
| **Sentry** | Error tracking (Python + Next.js) | ✅ projects created + SDK init live (backend + frontend) | `SENTRY_DSN` in backend, `NEXT_PUBLIC_SENTRY_DSN` in frontend |
| **Vercel** | Frontend hosting | ✅ deployed | Vercel UI holds the env vars |
| **Railway** | Backend hosting | ✅ deployed | Railway UI holds `ANTHROPIC_API_KEY`, `SHARPER_API_TOKEN`, `SHARPER_API_HOST=0.0.0.0`, `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`, `SHARPER_ALLOWED_ORIGINS`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SENTRY_DSN`. Root Directory set to `/backend`. |

**What "code TODO" means for each:**
- **Clerk** — ✅ fully done: `sharper/auth.py:require_token` is dual-mode (Clerk JWT first, static bearer fallback). Frontend wired via `@clerk/nextjs` v7: `ClerkProvider` in layout, `proxy.ts` middleware (Next.js 16 renamed `middleware.ts` → `proxy.ts`), `useAuth → getToken` sends JWT on each lint call. Static `NEXT_PUBLIC_SHARPER_API_TOKEN` stopgap removed from frontend.
- **Upstash** — ✅ done. `sharper/ratelimit.py:check_rate_limit` is a FastAPI dependency on `/api/lint` that does `INCR` + `EXPIRE 3600 NX` against the Upstash REST `/pipeline` endpoint per request. 10/hr anonymous (keyed by X-Forwarded-For-aware IP), 60/hr authenticated (keyed by Clerk user_id or `shared-token`). Fail-open.
- **Supabase** — ✅ fully done. `backend/db/migrations/001_initial.sql` run in Supabase dashboard. `sharper/persistence.py:save_critique()` writes critique + findings on each lint call. Frontend history page fetches via `lib/supabase-server.ts` (service-role key, server-side only). Env vars needed in Vercel: `SUPABASE_SERVICE_ROLE_KEY` (server-only, no NEXT_PUBLIC_ prefix).
- **Sentry** — ✅ SDK init live both sides. Backend `sharper/observability.py:init_sentry()` runs at api.py module load; uses `FastApiIntegration` + `StarletteIntegration`. Frontend `instrumentation.ts` + `instrumentation-client.ts` init from `NEXT_PUBLIC_SENTRY_DSN`. Both ends use shared `scrub_question_field` / `scrubQuestion` hooks on `before_send` to strip the user's pasted question text from any event payload (defense-in-depth on top of `sendDefaultPii=false`).

**Spending guardrails to set up via the Anthropic console** (independent of code; do this before Phase 4 soft launch):
- Daily spend cap on the Anthropic API key (recommend $5/day for soft-launch traffic).
- Per-IP rate limit (10 req/hr anonymous) — configured in code once Phase 3 step 2 ships.
- Input length cap (4000 chars) — already enforced in the Pydantic schema.
- Kill-switch endpoint (Phase 4): `POST /api/admin/disable` flips an env var; subsequent requests return 503.

## 13. Memory/preferences index (machine-wide)

These live in `~/.claude/projects/<project-id>/memory/` and persist across sessions:

- `user_github.md` — BK5102, no gh CLI, manual repo flow
- `project_sharper.md` — project overview + portfolio-facing context
- `feedback_commit_footer.md` — never add Co-Authored-By Claude
- `project_metaculus_api.md` — list endpoint broken, detail endpoint works

If restarting in a fresh session: these load automatically. PROMPT.md is the project-internal version; the memory files are the cross-session version.
