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

The Phase 1 exit criterion needs 30-50 real Metaculus questions with `ambiguous` / `clean` labels. The fetcher pulls recently-resolved ones for you to annotate.

```bash
# 1. Add METACULUS_API_TOKEN to .env (free token at metaculus.com profile page)
# 2. Pull 50 most-recently-resolved questions:
python -m scripts.fetch_metaculus --limit 50 --out data/questions.metaculus.jsonl

# 3. Open the file and fill in label + notes for each row.
#    label: "ambiguous" if the resolution was disputed, "clean" if not
#    notes: one-line summary of what went wrong (for ambiguous ones)
```

If Metaculus changes the API shape, run `--raw-first` to dump the first raw record and adjust `_to_record()` in [scripts/fetch_metaculus.py](scripts/fetch_metaculus.py).

## Layout

- `sharper/rubric.py` — the six rubric items (definitions + example failures). Edit this to tune the linter.
- `sharper/schema.py` — Pydantic models for the structured critique.
- `sharper/critic.py` — Anthropic API call with `client.messages.parse()`.
- `sharper/cli.py` — Typer entry point.
- `scripts/fetch_metaculus.py` — pulls resolved questions from the Metaculus API into JSONL.
- `data/questions.example.jsonl` — 5 hand-written examples; real data goes in `data/questions.metaculus.jsonl`.

## Phase 1 exit criteria

Rubric catches ≥8 of 10 known-ambiguous Metaculus questions in a held-out set; findings are specific (quote the offending span), not generic.
