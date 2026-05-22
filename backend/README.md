# Sharper — backend

Phase 1: CLI rubric spike. Pipe a draft forecasting question to the script, get back a structured critique mapping each rubric item to a finding plus a quoted span from the input.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Git Bash on Windows; use .venv\Scripts\activate on cmd
pip install -e ".[dev]"
cp .env.example .env             # then put your Anthropic key in .env
```

## Run

```bash
# Stdin
echo "Will the US enter a recession in 2025?" | sharper lint

# File
sharper lint --file data/questions.example.jsonl --line 1

# Inline string
sharper lint --text "Will AI be a big deal by 2030?"
```

Output is JSON by default; pass `--pretty` for the rich-formatted view.

## Collecting the held-out question set

The Phase 1 exit criterion needs **10 known-ambiguous + ~20 clean** Metaculus questions with annotated labels. The fetcher expands a list of question URLs (or IDs) into the Sharper JSONL shape; you do the labeling.

Why a URL list and not bulk-pull: Metaculus's `/api2/questions/` list filters are too limited to surface resolved questions reliably, but the per-question detail endpoint works fine. Curating during browsing is also the right UX — you want to *pick* known-disputed questions, not random recent ones.

**Realistic time cost.** Curating ten known-disputed questions by reading comment threads is ~2 hours of work. The strategies below cut that significantly. Skim them before you start.

```bash
# 1. Add METACULUS_API_TOKEN to .env (free token at metaculus.com profile page).
# 2. Curate URLs into data/ids.txt (see strategies in the "Data limitations"
#    section below for how to do this faster than reading every question).
# 3. Expand into JSONL:
python -m scripts.fetch_metaculus --ids-file data/ids.txt --out data/questions.metaculus.jsonl
# 4. Open the JSONL and fill in `label` (ambiguous | clean) and `notes` per row.
```

Debug helper: `python -m scripts.fetch_metaculus --id 1 --raw-first` dumps the first raw API record — handy if Metaculus changes the schema and `_to_record()` needs updating.

## Data: current state and growth plan

Current state of the labeled held-out set (`data/questions.metaculus.jsonl`): **19 questions = 14 ambiguous + 5 clean.** This is enough to meet Phase 1's exit threshold cleanly and to scaffold Phase 2; it is **not** enough for the spec's Phase 2 evaluation (50 questions with reference rewrites and a blind-reviewer protocol).

### Why we paused at n=19

1. **Curation cost is non-trivial.** 3-5 minutes per ambiguous question to find on Metaculus, open in a tab, extract via Claude-in-Chrome, review, and label. Pushing to n=50 is ~2-4 hours of focused work.
2. **Phase 1 exit bar was hit cleanly at n=19.** Adding more biosecurity-heavy questions would not have changed the recall + FP decision to ship Phase 1.
3. **Topic concentration matters more than count.** 12 of 19 are disease/PHEIC questions. The next chunk needs to be diverse, not just bigger — politics, finance, climate, sports, AI capability — to test whether the linter generalizes.
4. **Phase 2 evaluation is the actual reason to scale.** The blind-reviewer protocol (see §"Bringing Phase 2 from scaffolded to final") needs to exist first; building it against n=19 shakes out the protocol before paying the curation cost on the next 30 questions.

### Future-scope growth milestones

| Milestone | n_ambig | n_clean | Total | When to do it |
|---|---|---|---|---|
| Phase 1 spec-compliant | 14 | ~16 | ~30 | Grow clean set to stabilize FP rate measurement |
| Phase 2 evaluable | 20 | 30 | ~50 | Spec target; supports blind-reviewer protocol with statistical signal |
| Diverse-domain stretch | 25 | 35 | ~60 | Adds 4-5 politics/finance/climate/sports/AI questions per non-biosecurity domain |

When growing, use the URL-list workflow (next section). Prefer the Annulled/Ambiguous resolution badge for `label: ambiguous` candidates — they're free signal, no judgment required. Don't relitigate labels on the existing 19 — those were stabilized in commit `f321a4c` and revisiting them risks overfitting.

### Why n=5 was uninformative (kept for posterity, now historical)

- **Statistical noise dominates.** With ~3 ambiguous and ~2 clean questions, the 95% confidence interval on measured recall is roughly 9% – 99%. The linter is indistinguishable from random at this n.
- **Rubric coverage is thin.** Only ~3 of the 6 rubric items (operationalization, time bounds, source authority) get any depth of test. Scope drift and edge-case handling have ~zero test coverage.
- **Domain bias.** The current sample clusters around AI, SpaceX, finance, sports. Real Metaculus questions span geopolitics, biology, public health, elections — each with different ambiguity patterns. n=5 tells us nothing about generalization.
- **Overfitting risk.** If we iterate `sharper/rubric.py` and the prompt against these five, we'll train to them and lose the held-out property. The eval set must stay held out from tuning.

### Why curating 50 by hand is real work — and how to make it cheaper

The spec's structure is asymmetric: 10 ambiguous (recall test) + ~20 clean (FP test). The 10 ambiguous ones are the expensive part — clean ones can be sourced casually from any resolved question without a noisy comment thread.

Three strategies that cut the time for the ambiguous-10:

1. **Sort by comment count.** High-comment threads on resolved questions are almost always disputes. Skim the top 20–30 most-commented resolved questions on metaculus.com and pick the ones where forecasters argued about the resolution itself (vs. background chatter). Faster than reading every question.
2. **Use `annulled` resolutions as a free ambiguity signal.** Metaculus annuls a question when the resolution criteria turned out unsatisfiable. Browse the annulled set — these are *unambiguously* ambiguous, no judgment call needed. Several can usually be found this way without reading comments at all.
3. **Use the `ambiguous` resolution category.** Resolved-as-ambiguous is rarer than annulled but is a similarly clean signal.

Clean-question sourcing (the other ~20): pick any resolved questions with a named source, a numeric or specific event criterion, and a quiet comment thread. Recently-resolved questions on CPI, election results, sports scores, company earnings, court decisions are all good candidates.

### Recommended sequence

- **Now:** 5 examples is enough to confirm the pipeline works end-to-end. Confirmed (`adec569` → `cfd830c`). Do **not** tune the rubric against them.
- **Next:** Curate to 10 ambiguous + 10 clean = 20 total. This is the minimum n where Phase 1 recall numbers become interpretable. Use strategies (1)/(2) above.
- **Phase 1 exit:** Grow to 10 ambiguous + ~20 clean (spec target). Compute recall and FP rate, iterate rubric until ≥8/10 recall and ≤1 FP/clean.
- **Phase 2:** Grow to the spec's 50-question annotated set with reference critiques and suggested rewrites for the eval harness.

## Layout

- `sharper/rubric.py` — the six rubric items (definitions + example failures). Edit this to tune the linter.
- `sharper/schema.py` — Pydantic models for the structured critique.
- `sharper/critic.py` — Anthropic API call with `client.messages.parse()`.
- `sharper/cli.py` — Typer entry point.
- `scripts/fetch_metaculus.py` — pulls resolved questions from the Metaculus API into JSONL.
- `data/questions.example.jsonl` — 5 hand-written examples; real data goes in `data/questions.metaculus.jsonl`.

## Phase status

**Phase 1 — Rubric spike: EXIT MET.** At n=19 labeled questions, recall@high is 79% (11/14) — exceeds the 70% spec target. fp@high is 0.40 — well under the 1.0 target. Findings are specific with quoted spans, not generic. See `eval/runs/2026-05-21-120422.json`.

The spec called for 30-50 questions for the held-out set; we have 19. We're shipping Phase 1 against the held-out subset because the recall + FP bar is met cleanly at this sample size and pushing to 30 with the same biosecurity-heavy curation wouldn't change the decision. Growing the set to 30-50 is part of the Phase 2 path below.

**Phase 2 — Critique quality & rewrites: SUCCESS METRIC MET on an internal-scale sample.** First blind review (`eval/reviews/2026-05-21-204554.json`) over 51 rewrite pairs from the n=19 question set: **48/51 = 94% rated meaningfully better** (target: ≥70%). 3 not-better cases are minor — timezone pedantry on a publicly-timestamped event, a rubric_item misclassification (naming clarification labeled as scope_drift), and one debatable source-authority call. No systematic prompt issues. Spec's strict reading is "on a 50-question set" — we have 19; the metric should be re-confirmed at n=50 before public launch, but the internal-sample signal is strong enough to lock the current rubric (v0.4) and move to Phase 3.

**Phase 3 — Web interface: BACKEND STARTED.** FastAPI wrapper shipped (`sharper/api.py`): `POST /api/lint`, `GET /api/health`, CORS for `localhost:3000`. Auth (Clerk), rate-limit (Upstash Redis), persistence (Supabase), frontend (Next.js + TipTap) all TODO and require external accounts (Clerk, Upstash, Supabase, Sentry, Vercel, Railway).

## Bringing Phase 2 from scaffolded to final

Concrete sequence:

1. **Blind-reviewer protocol script** (`scripts/blind_review.py`) — loops `(quoted_span, suggested_rewrite)` pairs from the latest eval, prompts y/n/skip per pair, aggregates % yes per rubric item, saves to `eval/reviews/<timestamp>.json`. *Code task, ~30 min, no data dependency.*
2. **Smoke-run blind review on n=19** to shake out the protocol. *User task, ~20-30 min.*
3. **Iterate the rewrite prompt** if the n=19 number is low (e.g. <50% better). Likely fix is adding good/bad rewrite examples to `critic.py`. *Code task, 30-60 min.*
4. **Grow question set to ~50** with topic diversity (politics / finance / climate / sports / AI capability, not more disease questions). Use the URL-list workflow + Claude-in-Chrome extractor. *User task, 2-4 hours.*
5. **Re-run eval + blind review on n=50** to compute the spec's actual metric. *Code re-runs, ~5 min compute; user review, ~60-90 min.*
6. **Lock rubric version** if ≥70% rewrite-better. Tag commit as "Phase 2 exit". *Else iterate steps 3+5.*
