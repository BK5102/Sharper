"""Run the rubric linter against a labeled JSONL and compute recall + FP rate.

Builds the full linter input from each row (title + resolution_criteria + fine_print
+ background) so the linter sees what a forecaster sees -- not the title alone.

Usage:
    python -m scripts.run_eval
    python -m scripts.run_eval --input data/questions.metaculus.jsonl --limit 5
    python -m scripts.run_eval --out-dir eval/scratch    # scratch runs (gitignored)

Output:
    eval/runs/<timestamp>.json  -- per-row findings + summary metrics
    stderr                      -- human-readable summary

Metrics:
    recall@<sev>     fraction of ambiguous questions where the linter produced
                     at least one finding at severity >= <sev>
    fp_per_clean@<sev>  total findings of severity >= <sev> on clean questions,
                     divided by number of clean questions (spec target: <=1.0)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sharper.critic import MAX_INPUT_CHARS, critique_question

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


# Patterns that signal a resolver's after-the-fact meta-note inside the criteria
# text. Any paragraph (split by blank lines) containing one of these gets dropped
# at eval time -- otherwise the linter trivially "catches" scope_drift /
# ambiguity by reading the resolver's own annulment note.
_META_NOTE_PATTERNS = [
    re.compile(r"Note:\s*This question (was|is)\s+(resolved|annulled)", re.IGNORECASE),
    re.compile(r"^\s*EDIT[: ]+.*\b(resolved|annulled)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*This question (was |is )?(resolved|annulled)\s+(ambiguous|because)", re.IGNORECASE | re.MULTILINE),
    # "title and resolution criteria/criterion ... clash/clashed" -- matches both
    # 2750's "a clash was discovered between the title and resolution criteria"
    # and 2793's "title and resolution criterion clashed".
    re.compile(r"title and resolution criteri[oa]n[s]?.*\bclash", re.IGNORECASE | re.DOTALL),
    re.compile(r"a clash was discovered between the title", re.IGNORECASE),
]


def strip_resolver_meta_notes(text: str | None) -> str | None:
    """Drop paragraphs containing resolver after-the-fact meta-notes.

    Operates paragraph-by-paragraph (paragraphs separated by blank lines).
    Conservative: only matches very specific resolver-prefix shapes so we don't
    accidentally strip legitimate context that mentions resolution mechanics.
    """
    if not text:
        return text
    paragraphs = re.split(r"\n\s*\n", text)
    kept = [p for p in paragraphs if not any(pat.search(p) for pat in _META_NOTE_PATTERNS)]
    return "\n\n".join(kept).strip() or None


def build_question_text(row: dict[str, Any]) -> str:
    """Combine title + criteria + fine_print + background into one input string."""
    parts: list[str] = []
    if row.get("title"):
        parts.append(row["title"])
    # Strip resolver meta-notes from criteria + background before linting.
    rc = strip_resolver_meta_notes(row.get("resolution_criteria"))
    if rc:
        parts.append(f"\nResolution Criteria:\n{rc}")
    fp = strip_resolver_meta_notes(row.get("fine_print"))
    if fp:
        parts.append(f"\nFine Print:\n{fp}")
    bg = strip_resolver_meta_notes(row.get("background"))
    if bg:
        parts.append(f"\nBackground:\n{bg}")
    return "\n".join(parts)


def at_least(severity: str, findings: list[dict[str, Any]]) -> int:
    """Count findings whose severity is >= the given threshold."""
    thresh = SEVERITY_ORDER[severity]
    return sum(1 for f in findings if SEVERITY_ORDER[f["severity"]] >= thresh)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ambig = [r for r in results if r["label"] == "ambiguous"]
    clean = [r for r in results if r["label"] == "clean"]

    summary: dict[str, Any] = {
        "n_total": len(results),
        "n_ambiguous": len(ambig),
        "n_clean": len(clean),
        "recall": {},
        "fp_per_clean": {},
        "rubric_firing": {"ambiguous": {}, "clean": {}},
    }

    for sev in ("low", "medium", "high"):
        n_caught = sum(1 for r in ambig if at_least(sev, r["findings"]) > 0)
        summary["recall"][sev] = {
            "n_caught": n_caught,
            "n_total": len(ambig),
            "fraction": (n_caught / len(ambig)) if ambig else None,
        }
        total_fp = sum(at_least(sev, r["findings"]) for r in clean)
        summary["fp_per_clean"][sev] = {
            "total_findings": total_fp,
            "n_clean": len(clean),
            "per_question": (total_fp / len(clean)) if clean else None,
        }

    # Rubric item firing rates, partitioned by label
    for label in ("ambiguous", "clean"):
        counter: Counter[str] = Counter()
        for r in results:
            if r["label"] != label:
                continue
            for f in r["findings"]:
                counter[f["rubric_item"]] += 1
        summary["rubric_firing"][label] = dict(counter)

    return summary


def print_summary(summary: dict[str, Any], run_path: Path) -> None:
    p = lambda *a, **k: print(*a, file=sys.stderr, **k)  # noqa: E731
    p("\n=== SUMMARY ===")
    p(
        f"Total: {summary['n_total']} "
        f"({summary['n_ambiguous']} ambiguous + {summary['n_clean']} clean)"
    )
    p("\nRecall on ambiguous (>=1 finding at given severity):")
    for sev in ("low", "medium", "high"):
        d = summary["recall"][sev]
        frac = d["fraction"]
        if frac is None:
            p(f"  >={sev:6s}: n/a (no ambiguous rows)")
        else:
            p(f"  >={sev:6s}: {d['n_caught']}/{d['n_total']} = {frac * 100:.0f}%")

    p("\nFalse positives on clean (findings per question):")
    for sev in ("low", "medium", "high"):
        d = summary["fp_per_clean"][sev]
        pq = d["per_question"]
        if pq is None:
            p(f"  >={sev:6s}: n/a (no clean rows)")
        else:
            p(f"  >={sev:6s}: {d['total_findings']} total / {d['n_clean']} = {pq:.2f} per question")

    p("\nRubric items firing on ambiguous:")
    for k, v in sorted(summary["rubric_firing"]["ambiguous"].items(), key=lambda x: -x[1]):
        p(f"  {k:35s} {v}")
    p("\nRubric items firing on clean (these are FPs):")
    for k, v in sorted(summary["rubric_firing"]["clean"].items(), key=lambda x: -x[1]):
        p(f"  {k:35s} {v}")
    p(f"\nDetailed run saved to: {run_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/questions.metaculus.jsonl"),
        help="Labeled JSONL to eval against.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("eval/runs"),
        help="Where to write the dated run JSON. Use eval/scratch/ for throwaway runs.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Eval only the first N rows (debugging)."
    )
    parser.add_argument(
        "--note",
        type=str,
        default="",
        help="Optional note saved into the run JSON (e.g. rubric version).",
    )
    args = parser.parse_args(argv)

    load_dotenv(override=True)
    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if r.get("label") in ("ambiguous", "clean")]
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print("error: no labeled rows found (label must be 'ambiguous' or 'clean')", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    skipped: list[str] = []
    for i, row in enumerate(rows, 1):
        qtext = build_question_text(row)
        if len(qtext) > MAX_INPUT_CHARS:
            print(
                f"[{i}/{len(rows)}] {row['id']} SKIP: {len(qtext)} chars > {MAX_INPUT_CHARS}",
                file=sys.stderr,
            )
            skipped.append(row["id"])
            continue
        print(
            f"[{i}/{len(rows)}] {row['id']} ({row['label']}) ...",
            file=sys.stderr,
            end=" ",
            flush=True,
        )
        try:
            critique = critique_question(qtext)
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            skipped.append(row["id"])
            continue
        print(f"{len(critique.findings)} findings", file=sys.stderr)
        results.append(
            {
                "id": row["id"],
                "label": row["label"],
                "title": row["title"],
                "n_input_chars": len(qtext),
                "findings": [f.model_dump(mode="json") for f in critique.findings],
                "overall_assessment": critique.overall_assessment,
            }
        )

    summary = summarize(results)

    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_path = args.out_dir / f"{timestamp}.json"
    run_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "input": str(args.input),
                "note": args.note,
                "skipped": skipped,
                "summary": summary,
                "per_row": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print_summary(summary, run_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
