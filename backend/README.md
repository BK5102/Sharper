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

## Data limitations and path to a real eval set

The 5 hand-written questions in `questions.example.jsonl` and the 5 user-curated Metaculus questions in `questions.metaculus.jsonl` are a **smoke test, not a held-out eval set**. Don't read any signal from recall or false-positive rates computed at this sample size.

### Why n=5 is uninformative

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

## Phase 1 exit criteria

Rubric catches ≥8 of 10 known-ambiguous Metaculus questions in a held-out set; findings are specific (quote the offending span), not generic. **Status:** specificity confirmed at n=5 smoke-test scale (`93c43a1`); recall measurement is gated on curating the held-out set per "Data limitations" above. Not yet at exit.
