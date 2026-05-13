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

The Phase 1 exit criterion needs 30-50 real Metaculus questions with `ambiguous` / `clean` labels. The fetcher expands a list of question URLs (or IDs) into the Sharper JSONL shape.

Why a URL list and not bulk-pull: Metaculus's `/api2/questions/` list filters are too limited to surface resolved questions reliably, but the per-question detail endpoint works fine. Curating during browsing is also the right UX — you want to *pick* known-disputed questions, not random recent ones.

```bash
# 1. Add METACULUS_API_TOKEN to .env (free token at metaculus.com profile page).
# 2. Browse metaculus.com for resolved questions. Especially look for ones with
#    comment threads where forecasters argued about the resolution -- those are
#    your known-ambiguous targets. Aim for ~25 ambiguous + ~25 clean.
# 3. Paste one URL (or bare ID) per line into data/ids.txt:
#       https://www.metaculus.com/questions/1234/some-question-slug/
#       5678
#       # lines starting with # are ignored
# 4. Expand into JSONL:
python -m scripts.fetch_metaculus --ids-file data/ids.txt --out data/questions.metaculus.jsonl
# 5. Open the JSONL and fill in `label` (ambiguous | clean) and `notes` per row.
```

Debug helper: `python -m scripts.fetch_metaculus --id 1 --raw-first` dumps the first raw API record — handy if Metaculus changes the schema and `_to_record()` needs updating.

## Layout

- `sharper/rubric.py` — the six rubric items (definitions + example failures). Edit this to tune the linter.
- `sharper/schema.py` — Pydantic models for the structured critique.
- `sharper/critic.py` — Anthropic API call with `client.messages.parse()`.
- `sharper/cli.py` — Typer entry point.
- `scripts/fetch_metaculus.py` — pulls resolved questions from the Metaculus API into JSONL.
- `data/questions.example.jsonl` — 5 hand-written examples; real data goes in `data/questions.metaculus.jsonl`.

## Phase 1 exit criteria

Rubric catches ≥8 of 10 known-ambiguous Metaculus questions in a held-out set; findings are specific (quote the offending span), not generic.
