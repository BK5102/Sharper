# Sharper — Project Reference

This file is a self-contained snapshot of the project: what it is, the decisions made, the architecture chosen, the gotchas hit, and the exact recipe to recreate it from scratch. Read this first if returning to the project after a break or rebuilding from zero.

Last updated: 2026-05-21. **Keep this file in sync** with every meaningful change (rubric edits, schema changes, eval workflow changes, new gotchas).

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
└── backend/
    ├── pyproject.toml             # deps: anthropic, pydantic, typer, rich, python-dotenv; dev: pytest, ruff
    ├── README.md                  # backend setup + held-out data workflow + data limitations
    ├── .env.example               # ANTHROPIC_API_KEY, SHARPER_MODEL, METACULUS_API_TOKEN
    ├── sharper/                   # main package (installed editable as `sharper`)
    │   ├── __init__.py
    │   ├── schema.py              # Pydantic Finding + Critique models
    │   ├── rubric.py              # 6 rubric items as frozen dataclass tuple
    │   ├── critic.py              # critique_question() via client.messages.parse(output_format=Critique)
    │   └── cli.py                 # `sharper lint` Typer entry point
    ├── scripts/
    │   ├── __init__.py
    │   ├── fetch_metaculus.py     # per-question detail-endpoint fetcher
    │   └── run_eval.py            # eval harness: recall + FP/clean at three severity cuts
    ├── tests/
    │   ├── test_smoke.py          # rubric integrity, prompt assembly, schema round-trip
    │   └── test_fetch_metaculus.py
    ├── data/
    │   ├── ids.example.txt        # placeholder URL list
    │   ├── ids.txt                # user-curated URLs (5 initial + 8 ambiguous + 6 more = 19)
    │   ├── questions.example.jsonl    # 5 hand-written examples
    │   └── questions.metaculus.jsonl  # 19 labeled questions (9 ambiguous + 10 clean)
    └── eval/runs/                 # dated eval history JSON (committed)
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

---

## 8. Current state (as of 2026-05-21, post-relabel + meta-strip)

**Built and working:**
- ✅ Backend scaffold (`pyproject.toml`, `sharper/` package, tests)
- ✅ Six-item rubric with definitions + example failures
- ✅ Pydantic Finding + Critique schemas
- ✅ Anthropic API call via `client.messages.parse(output_format=Critique)` with prompt caching
- ✅ Typer CLI: stdin / `--text` / `--file` / `--line` / `--pretty`
- ✅ Metaculus per-ID fetcher with URL/ID list input + UTF-8 stdout
- ✅ Claude-in-Chrome scraper prompt + JS extractor for full criteria text
- ✅ Eval harness with three-severity recall + FP metrics, dated run JSON history
- ✅ **Resolver-meta-note stripper** in `run_eval.py` (drops paragraphs with "Note: This question was resolved ambiguous", "title and resolution criteria clash", etc.) — prevents gold-label leakage in question 2750-style cases
- ✅ 19-question labeled held-out set (**14 ambiguous + 5 clean** after relabeling 5 marginal rows)
- ✅ Two eval runs committed

**Phase 1 status**: pipeline producing real discrimination now. See §9 for current numbers.

**Not yet built:**
- Phase 2: suggested rewrites, eval harness with per-row "actual disputed issue" annotations, blind reviewer protocol
- Phase 3: FastAPI wrapper, Next.js frontend, Clerk auth, Supabase, history page
- Phase 4: Vercel/Railway deploy, public demo, methodology writeup

---

## 9. Eval results history

| run | n_ambig | n_clean | recall@high | recall@med | recall@low | fp@high | fp@med | fp@low | notes |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-20-220054 | 9 | 10 | 22% | 100% | 100% | 0.90 | 2.70 | 3.70 | First eval. 100% recall@low is "flag everything"; per-q mean 3.33 ambig / 3.70 clean — anti-discriminating. |
| 2026-05-21-113655 | 14 | 5 | **50%** | 100% | 100% | **0.00** | 1.20 | 2.60 | Meta-stripper + relabeled 5 marginal clean → ambiguous. fp@high → 0 (perfect on strict-clean), recall@high up 28 pts, per-q mean 4.07 ambig / 2.60 clean (real discrimination). |

**Phase 1 exit thresholds**: recall ≥70%, FP/clean ≤1.0. Current gap: recall@high 50% (need +20 pts), fp@medium 1.20 (need ≤1.0).

The 7 ambiguous questions where the linter is lukewarm (medium findings, no high) are exactly the "subtle dispute" cases — annulled questions where the criteria looked OK but an edge case bit. The linter catches the issue but doesn't escalate severity. **This is the next tunable lever** (rubric severity definitions).

The 5 clean questions all get 0 high-severity findings. The rubric's "high" threshold is working correctly.

---

## 10. Open issues / next steps

In priority order:

1. ✅ **Strip resolver meta-notes from criteria text** — done in `run_eval.py`, tested.
2. ✅ **Tighten clean labels** — done; 5 rows relabeled to ambiguous.
3. ✅ **Re-run eval** — done; numbers in §9.
4. **Rubric tuning to raise high-severity recall to 70%.** Currently 50%. The lukewarm-on-subtle-disputes pattern is the lever — the rubric's severity definitions should push the model to escalate when issue involves words like "credible sources", "approximately", "may", "if available", "best judgment". Don't touch rubric items themselves yet; tune the severity language in `schema.py` and the system prompt in `critic.py`.
5. **Per-row "actual disputed issue" annotations on ambiguous rows.** Spec recall is "linter flags ≥1 of the *actual* disputed issues" — we measure "linter flags ≥1 of anything". ~30 min of human work for n=14. Would unlock measuring the spec's true criterion.
6. **More truly-clean questions.** n=5 clean is too few for a stable FP measurement. Need ~10. Curate from politics/finance/sports questions with crisp criteria.
7. **Topic diversity.** Set is 12/19 disease/PHEIC. Add 5-10 questions from other domains (geopolitics, AI capability benchmarks, market thresholds, climate records).
8. **Phase 2 entry**: suggested-rewrite generation per finding. Extend `Finding` schema with `suggested_rewrite: str | None`; update system prompt; add blind-reviewer protocol.

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

## 12. Memory/preferences index (machine-wide)

These live in `~/.claude/projects/<project-id>/memory/` and persist across sessions:

- `user_github.md` — BK5102, no gh CLI, manual repo flow
- `project_sharper.md` — project overview + portfolio-facing context
- `feedback_commit_footer.md` — never add Co-Authored-By Claude
- `project_metaculus_api.md` — list endpoint broken, detail endpoint works

If restarting in a fresh session: these load automatically. PROMPT.md is the project-internal version; the memory files are the cross-session version.
