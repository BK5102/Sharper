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

## Layout

- `sharper/rubric.py` — the six rubric items (definitions + example failures). Edit this to tune the linter.
- `sharper/schema.py` — Pydantic models for the structured critique.
- `sharper/critic.py` — Anthropic API call with `client.messages.parse()`.
- `sharper/cli.py` — Typer entry point.
- `data/questions.example.jsonl` — placeholder for the 30-50 collected Metaculus questions (replace with real data).

## Phase 1 exit criteria

Rubric catches ≥8 of 10 known-ambiguous Metaculus questions in a held-out set; findings are specific (quote the offending span), not generic.
