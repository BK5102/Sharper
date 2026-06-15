# Sharper

A writing linter for structured forecasting questions. Paste a draft question and get a rubric-driven critique: the exact phrase that's ambiguous, why it would cause a disputed outcome, and a suggested rewrite.

Built initially for prediction market platforms (Metaculus), but the quality problems it catches — vague resolution criteria, unmeasurable thresholds, missing time bounds, contested sources — show up in any context where people write structured forecasting questions: civic scenario planning, public health program evaluation, nonprofit outcome goal-setting. The rubric is domain-agnostic.

## What it does

- **Paste a draft question** (title, optional resolution criteria, background) and get a rubric-driven critique.
- **Rubric coverage**: resolution criteria clarity, time bounds, operationalization of fuzzy terms, edge cases, source authority, scope drift.
- **Inline flagging**: every issue is tied to the exact span that triggered it.
- **Suggested rewrites**: concrete alternative phrasing per issue — accept, edit, or ignore.
- **Severity ranking**: ranked by likelihood of causing a disputed outcome, not model confidence.
- **Per-user history**: revisit past critiques and spot recurring patterns in your own writing.

## Who it's for

- **Metaculus question-authors** writing public forecasting questions — the original use case.
- **Civic organizations and local government** that write goal and outcome statements for scenario planning (city sustainability offices, regional planning agencies).
- **Public health and nonprofit teams** writing program outcome questions ("Will 80% of participants reduce A1C by ≥0.5 by program exit?") where vague criteria lead to disputed program evaluations.

## Non-goals

Not a forecaster, not a probability estimator, not a general-purpose grammar checker. Scope is structured-question writing quality.

## Success criteria

- ≥70% recall on real disputed-question issues from a held-out set of Metaculus questions.
- ≤1 false-positive flag per question on clean, never-disputed questions.
- Blind reviewer prefers suggested rewrite over original on ≥70% of test questions.

## Stack

**Backend** — Python 3.11+, FastAPI, Anthropic Claude API (Sonnet), Pydantic for structured output.

**Frontend** — Next.js 16 (App Router) + TypeScript, Tailwind CSS 4, TipTap for inline span highlighting and click-to-accept rewrites.

**Auth & storage** — Supabase (email/password auth + Postgres history, keyed by user ID).

**Infra** — Vercel (frontend), Railway (backend), Upstash Redis (rate limiting), Sentry (errors).

**Eval & CI** — pytest + custom eval script, labeled JSONL test set in git, dated eval-history JSON.

**Cost controls** — 10 req/hr anonymous per-IP, daily spend cap on the Anthropic key, ~4,000 char input cap.

## Build plan

| Phase | Theme | Output | Exit criteria | Status |
| --- | --- | --- | --- | --- |
| 1 | Rubric spike | CLI returning structured critique against hand-built rubric | Catches ≥8/10 known-ambiguous questions; findings are specific, not generic | ✅ Met (recall@high 79%, fp@high 0.40 at n=19 labeled questions) |
| 2 | Critique quality & suggestions | Per-issue rewrites + eval harness | Rewrites rated "meaningfully better" by blind reviewer on ≥70% of test questions | ✅ Met on internal sample (94% rewrite-better across 51 pairs) |
| 3 | Web interface | Next.js + FastAPI app with auth, inline-flagged editor, accept/reject rewrites, history page | Paste-to-critique <5s; signup-to-first-critique <30s; history loads across devices | ✅ Complete — both Vercel and Railway deploys live |
| 4 | Polish & distribution | Hosted demo, methodology writeup, soft launch | Public for 7 days within spend cap; ≥1 rubric item fires per session on average | Not started |
| 5 | Civic/nonprofit extension | Rubric tuned for civic/policy questions; one real deployment + case study | One documented real-world deployment; case study published | Not started |

## Current status (2026-06-15)

- **Full stack is live.** Next.js 16 frontend on Vercel, FastAPI backend on Railway. Supabase auth (email/password) wired end-to-end. Signed-in users get 60 req/hr vs 10 req/hr anonymous.
- **Phase 1–3 complete.** Rubric meets spec targets (recall@high 79%, fp@high 0.40). Blind review on 51 rewrite pairs scored 94% rewrite-better. All 14 Phase 3 web interface steps coded and deployed.
- **Strategic pivot underway.** Sharper's rubric applies directly to civic/nonprofit scenario planning questions — the quality problems are identical. Phase 5 targets real deployments: Metaculus question-authors (easiest path), Sacramento-area civic orgs (City of Sacramento Office of Innovation and Sustainability, SACOG), and local public health nonprofits (Sacramento County DHHS, NDPP affiliates).
