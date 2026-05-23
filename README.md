# Sharper

A writing tool that helps forecasters and question-authors catch ambiguity, fuzzy resolution criteria, and missing operationalization before a question goes live. Targets the well-known quality problems in platforms like Metaculus, where vague wording leads to disputed resolutions and wasted forecaster attention.

## What it does

- **Paste a draft question** (title, optional resolution criteria, background) and get a rubric-driven critique.
- **Rubric coverage**: resolution criteria clarity, time bounds, operationalization of fuzzy terms, edge cases, source authority, scope drift.
- **Inline flagging**: every issue is tied to the exact span that triggered it.
- **Suggested rewrites**: concrete alternative phrasing per issue — accept, edit, or ignore.
- **Severity ranking**: ranked by likelihood of causing a disputed resolution, not model confidence.
- **Per-user history**: revisit past critiques and spot recurring patterns in your own writing.

## Non-goals

Not a forecaster, not a Metaculus integration, not a team collaboration tool, not a general-purpose grammar checker. Scope is narrow to forecasting-question quality.

## Success criteria

- ≥70% recall on real disputed-question issues from a held-out set of 50 Metaculus questions.
- ≤1 false-positive flag per question on clean, never-disputed questions.
- Blind reviewer prefers suggested rewrite over original on ≥70% of test questions.

## Stack

**Backend** — Python 3.11+, FastAPI, Anthropic Claude API (Sonnet), Pydantic for structured output.

**Frontend** — Next.js 14 (App Router) + TypeScript, Tailwind + shadcn/ui, TipTap (or contenteditable) for inline span highlighting and click-to-accept rewrites.

**Auth & storage** — Clerk (magic link + Google OAuth), Supabase Postgres keyed by Clerk user ID.

**Infra** — Vercel (frontend), Railway (backend), Upstash Redis (rate limiting), Sentry (errors).

**Eval & CI** — pytest + custom eval script, 50-question annotated JSONL test set in git, dated eval-history JSON, GitHub Actions failing the PR if recall drops.

**Cost controls** — 10 req/hr anonymous per-IP, daily spend cap on the Anthropic key, ~4,000 char input cap, kill-switch endpoint.

## Build plan

| Phase | Theme | Output | Exit criteria | Status |
| --- | --- | --- | --- | --- |
| 1 | Rubric spike | CLI returning structured critique against hand-built rubric | Catches ≥8/10 known-ambiguous questions; findings are specific, not generic | ✅ Met (recall@high 79%, fp@high 0.40 at n=19 labeled questions) |
| 2 | Critique quality & suggestions | Per-issue rewrites + eval harness vs. hand-annotated references | Rewrites rated "meaningfully better" by blind reviewer on ≥70% of 50-question eval set | ✅ Met on internal sample (94% rewrite-better across 51 pairs from n=19 questions); confirm at n=50 before public launch |
| 3 | Web interface | Next.js + FastAPI app with auth, inline-flagged editor, accept/reject rewrites, history page | Paste-to-critique <5s; signup-to-first-critique <30s; history loads across devices | 6 / 14 steps done. **Deploys live on Vercel + Railway.** Static-bearer auth gates the public endpoint; Clerk JWT / Upstash rate limit / Supabase persistence / Sentry SDK still to integrate (accounts all configured) |
| 4 | Polish & distribution | Hosted demo, README with examples, rubric/eval writeup | Public for 7 days without spend-cap breach or downtime; ≥1 rubric item fires per session on average | Not started |

## Current status (2026-05-22)

- **Linter is live end-to-end and deployed.** Next.js frontend on Vercel, FastAPI backend on Railway. Static-bearer auth gates the public `/api/lint` endpoint until Clerk JWT verification ships; the bearer is a stopgap, not real per-user auth.
- **Held-out set is at n=19** (14 ambiguous + 5 clean) — under the spec's 50-question target. Bulk scraping isn't an option (Metaculus API doesn't expose resolution criteria; web pages are Cloudflare-protected against non-browser clients), so curation runs one tab at a time via a Claude-in-Chrome extractor at ~3-5 min per question. Growing to n=50 is ~1.5-2.5 hours of focused work and is deferred until pre-public-launch. See [`backend/README.md`](backend/README.md#data-current-state-and-growth-plan).
- **Phase 1 exit met** at high severity (recall@high 79%, fp@high 0.40 — both well past spec targets).
- **Phase 2 success metric met on internal sample.** Blind review on 51 rewrite pairs scored 94% rewrite-better (target ≥70%). Re-confirmation at n=50 questions before any public launch.
- **Phase 3 — backend + frontend deployed; integration code is the remaining gate.** Six of fourteen Phase 3 steps done (FastAPI wrapper, Next.js scaffold, TipTap editor, example gallery, Vercel deploy, Railway deploy). All six external service accounts (Clerk, Upstash, Supabase, Sentry, Vercel, Railway) are configured with keys in `.env` files. Remaining: Clerk JWT verification, Upstash rate-limit middleware, Supabase persistence layer + history page, Sentry SDK init.
