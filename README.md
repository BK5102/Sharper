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

| Phase | Theme | Output | Exit criteria |
| --- | --- | --- | --- |
| 1 | Rubric spike | CLI returning structured critique against hand-built rubric | Catches ≥8/10 known-ambiguous questions; findings are specific, not generic |
| 2 | Critique quality & suggestions | Per-issue rewrites + eval harness vs. hand-annotated references | Rewrites rated "meaningfully better" by blind reviewer on ≥70% of 50-question eval set |
| 3 | Web interface | Next.js + FastAPI app with auth, inline-flagged editor, accept/reject rewrites, history page | Paste-to-critique <5s; signup-to-first-critique <30s; history loads across devices |
| 4 | Polish & distribution | Hosted demo, README with examples, rubric/eval writeup | Public for 7 days without spend-cap breach or downtime; ≥1 rubric item fires per session on average |
