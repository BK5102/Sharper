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
    ├── pyproject.toml             # deps: anthropic, pydantic, typer, rich, python-dotenv, fastapi, uvicorn; dev: pytest, ruff, httpx
    ├── README.md                  # backend setup + held-out data workflow + data limitations
    ├── .env.example               # ANTHROPIC_API_KEY, SHARPER_MODEL, METACULUS_API_TOKEN
    ├── sharper/                   # main package (installed editable as `sharper`)
    │   ├── __init__.py
    │   ├── schema.py              # Pydantic Finding + Critique models
    │   ├── rubric.py              # 6 rubric items as frozen dataclass tuple
    │   ├── critic.py              # critique_question() via client.messages.parse(output_format=Critique)
    │   ├── cli.py                 # `sharper lint` Typer entry point
    │   └── api.py                 # FastAPI app with POST /api/lint + GET /api/health; `sharper-api` script
    ├── scripts/
    │   ├── __init__.py
    │   ├── fetch_metaculus.py     # per-question detail-endpoint fetcher
    │   └── run_eval.py            # eval harness: recall + FP/clean at three severity cuts
    ├── tests/
    │   ├── test_smoke.py          # rubric integrity, prompt assembly, schema round-trip
    │   ├── test_fetch_metaculus.py
    │   ├── test_run_eval.py       # meta-note stripper, build_question_text, summarize
    │   └── test_api.py            # FastAPI endpoint contract (TestClient + mock)
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

---

## 8. Current state (as of 2026-05-21, post-relabel + meta-strip)

**Built and working:**
- ✅ Backend scaffold (`pyproject.toml`, `sharper/` package, tests)
- ✅ Six-item rubric with definitions + example failures
- ✅ Pydantic Finding + Critique schemas — Finding includes `suggested_rewrite: str | None`
- ✅ Anthropic API call via `client.messages.parse(output_format=Critique)` with prompt caching
- ✅ Typer CLI: stdin / `--text` / `--file` / `--line` / `--pretty`
- ✅ **FastAPI wrapper** (`sharper/api.py`): `POST /api/lint`, `GET /api/health`, CORS, `sharper-api` console script
- ✅ Metaculus per-ID fetcher with URL/ID list input + UTF-8 stdout
- ✅ Claude-in-Chrome scraper prompt + JS extractor for full criteria text
- ✅ Eval harness with three-severity recall + FP metrics, dated run JSON history
- ✅ Resolver-meta-note stripper in `run_eval.py` — prevents gold-label leakage
- ✅ Severity calibration tuned to escalate on discretionary language
- ✅ 19-question labeled held-out set (14 ambiguous + 5 clean)
- ✅ Four eval runs committed

**Phase 1 status**: **EXIT MET** at high severity (recall@high 79% vs 70% target; fp@high 0.40 vs 1.0 target). Spec target of 30-50 questions for the held-out set is **under-met** — we're at 19. See §9 for why this is OK to ship Phase 1 against but blocks Phase 2 measurement.
**Phase 2 status**: **scaffolded, blind-reviewer protocol shipped, not yet evaluated.** The linter emits `suggested_rewrite`, sample inspection looks good, and `scripts/blind_review.py` is ready to run. The spec's success criterion ("rewrites rated meaningfully better by blind reviewer on ≥70% of a 50-question set") has not been measured yet. Next step: smoke-run the protocol on the current n=19 to shake out the UX before scaling. See §10.
**Phase 3 status**: FastAPI wrapper shipped. Auth (Clerk), rate-limit (Upstash Redis), persistence (Supabase), frontend (Next.js) still TODO — see §13 account-setup steps.

**Not yet built:**
- Phase 2: suggested rewrites, eval harness with per-row "actual disputed issue" annotations, blind reviewer protocol
- Phase 3: FastAPI wrapper, Next.js frontend, Clerk auth, Supabase, history page
- Phase 4: Vercel/Railway deploy, public demo, methodology writeup

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

The spec calls for 30-50 questions in Phase 1 and a 50-question annotated set in Phase 2. We currently have 19. Reasons we paused at 19 rather than pushing on to 50:

1. **Per-question curation cost.** Each ambiguous question requires: (a) finding it on Metaculus by scrolling Resolved+Binary for Annulled/Ambiguous badges, (b) opening it in a browser tab, (c) running the Claude-in-Chrome extractor across all open tabs, (d) reviewing the resulting JSONL, (e) deciding labels for any Yes/No-resolved rows where the script's auto-label couldn't help. Rough rate: 1-3 minutes per ambiguous question for steps (a) and (b), plus 3-5 minutes for steps (d)/(e). Curating the next 30 questions is roughly 2-4 hours of focused work — a real, but not unrealistic, ask.
2. **Diminishing return on Phase 1.** Phase 1's exit criterion is a recall + FP bar that we hit at n=19. Pushing to n=30 would mostly add noise around an already-met threshold rather than change the decision to move to Phase 2.
3. **Topic concentration risk increases the value of MORE diverse questions, not just MORE questions.** Current set is 12/19 disease/PHEIC; pushing to 30 by scraping more biosecurity questions would not meaningfully test generalization. The diversity-first growth plan (politics, finance, climate, sports, AI capability) requires more deliberate curation, not bulk scraping.
4. **Phase 2 measurement is the actual gate for going larger.** The blind-reviewer protocol (see §10) requires the user to write reference rewrites per finding — that's the slow part. Building it against n=19 first lets us shake out the protocol before paying the curation cost on 30 more questions. Once the protocol is built and the rate is calibrated, scaling becomes a straight execution path.

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
| 2 | **Run blind review on n=19 to shake out the protocol.** Will produce a preliminary % rewrite-better number; small sample so don't treat the number as final, but the protocol bugs will surface here. | data (user) | 20-30 min of focused review | first reviews/*.json artifact |
| 3 | **Iterate the rewrite prompt if the n=19 number is low** (e.g. <50%). The fix is in `critic.py` system prompt — likely adding examples of good vs bad rewrites. | code | 30-60 min | new commit, new eval run |
| 4 | **Grow the question set to ~50** using the milestones in §9 future scope. Prioritize diversity (politics / finance / climate / sports / AI capability) over volume — 30 diverse questions beats 50 biosecurity questions. | data (user) | 2-4 hrs of focused curation | updated `data/questions.metaculus.jsonl` |
| 5 | **Re-run eval against n=50** to regenerate per-finding rewrites. | code (re-runs) | 5 min compute | new `eval/runs/*.json` |
| 6 | **Run blind review against n=50** to compute the spec's actual metric. | data (user) | 60-90 min of focused review | final `eval/reviews/*.json` |
| 7 | **Decision point**: if ≥70% rewrite-better, lock rubric v0.4 (or whatever) and tag the commit as "Phase 2 exit". If below, iterate steps 3+5+6. | code+data | 1-2 cycles | tagged commit |

**Optional but valuable parallel work:**

- **Per-row "actual disputed issue" annotations on ambiguous rows.** Spec recall is "linter flags ≥1 of the *actual* disputed issues"; we currently measure "≥1 of anything", a weaker proxy. ~5 min per ambiguous row to write the actual dispute reason into `notes`. Unlocks measuring the spec's true criterion.
- **Reference rewrites per finding**, against which the model's rewrite is scored. The blind-reviewer protocol above is the cheaper version of this — it skips the reference and just asks "is the model's rewrite better than the original?". Adding gold references would let us additionally measure "how close to the human-quality rewrite did the model get?".

**Phase 3 — Web Interface (after Phase 2 exit)**

| # | Step | Owner | Account needed | Effort |
|---|---|---|---|---|
| 1 | ✅ **FastAPI wrapper** (`POST /api/lint`, `GET /api/health`) | code | — | done |
| 2 | **Per-IP rate limiting** middleware via Upstash Redis (10 req/hr anonymous). | code | Upstash | 1 hr |
| 3 | **Clerk auth middleware**: verify JWT on protected routes, extract `user_id`. | code | Clerk | 1-2 hrs |
| 4 | **Per-user rate limiting** (overrides per-IP for authenticated users). | code | Upstash + Clerk | 30 min |
| 5 | **Supabase tables + persistence**: `critiques`, `findings`, `rewrite_actions`, keyed by Clerk `user_id`. Schema migration in `backend/db/`. | code | Supabase | 2-3 hrs |
| 6 | **Next.js 14 scaffold** (`frontend/`), paste area + critique view, hits `POST /api/lint`. No auth yet. | code | — | 3-4 hrs |
| 7 | **TipTap editor integration** with inline span highlighting; click-to-accept rewrite replaces the span in place. | code | — | 3-5 hrs |
| 8 | **Clerk frontend integration** + protected routes (history page). | code | Clerk | 1-2 hrs |
| 9 | **History page**: server-side fetch from Supabase by `user_id`, list past critiques. | code | Supabase | 2 hrs |
| 10 | **Example gallery** on landing page: 3-4 before/after examples from the eval set. | code | — | 1 hr |
| 11 | **Sentry integration** (frontend + backend). | code | Sentry | 30 min |
| 12 | **Vercel deploy** for the frontend; wire `NEXT_PUBLIC_API_URL` to the Railway backend URL. | code | Vercel + Railway | 30 min |
| 13 | **Railway deploy** for the FastAPI backend; wire all the secrets from earlier steps. | code | Railway | 1 hr |
| 14 | **Soft launch** to 1-2 forecasting communities (Reddit, Twitter, Manifold Markets discord). | data (user) | — | 30 min |

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

## 12. Account setup checklist (for Phase 3+)

Phase 3 needs five external services. Free-tier accounts are sufficient for development and a soft launch. Setup is do-once-per-service, ~10 min each. Add the resulting credentials to `backend/.env`.

| Service | Use | URL | Env vars to add |
|---|---|---|---|
| **Anthropic** ✅ | Claude API for the linter | console.anthropic.com | `ANTHROPIC_API_KEY` (already set) |
| **Metaculus** ✅ | Question fetcher | metaculus.com → profile → API token | `METACULUS_API_TOKEN` (already set) |
| **Clerk** | Auth (magic link + Google OAuth) | clerk.com → create app → "Sharper" | `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` |
| **Upstash** | Redis for rate limiting | upstash.com → create Redis DB (free tier) | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` |
| **Supabase** | Postgres for per-user history | supabase.com → create project (free tier) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| **Sentry** | Error tracking (Python + Next.js) | sentry.io → create project | `SENTRY_DSN` |
| **Vercel** | Frontend hosting | vercel.com → connect GitHub repo | (set via UI; deploy from `frontend/`) |
| **Railway** | Backend hosting | railway.app → connect GitHub repo | (set via UI; deploy from `backend/`) |

**Setup order**: Clerk → Upstash → Supabase first (these block backend code work in Phase 3 steps 2-5). Sentry/Vercel/Railway last (these block deploy, Phase 3 steps 11-13). No account is needed for Phase 2 or for finishing the FastAPI work locally.

**Spending guardrails** (set once, on the Anthropic console):
- Daily spend cap on the Anthropic API key (recommend $5/day for soft-launch traffic).
- Per-IP rate limit (10 req/hr anonymous) configured in code via Upstash.
- Input length cap (4000 chars) enforced in the Pydantic schema.
- Kill-switch endpoint (Phase 4 work): `POST /api/admin/disable` flips an env var; subsequent requests return 503.

## 13. Memory/preferences index (machine-wide)

These live in `~/.claude/projects/<project-id>/memory/` and persist across sessions:

- `user_github.md` — BK5102, no gh CLI, manual repo flow
- `project_sharper.md` — project overview + portfolio-facing context
- `feedback_commit_footer.md` — never add Co-Authored-By Claude
- `project_metaculus_api.md` — list endpoint broken, detail endpoint works

If restarting in a fresh session: these load automatically. PROMPT.md is the project-internal version; the memory files are the cross-session version.
