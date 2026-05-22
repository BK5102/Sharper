"""Blind-reviewer protocol for Phase 2 success criterion.

Loops over (quoted_span, suggested_rewrite) pairs from the latest eval run.
For each pair, shows only the question title + original span + proposed rewrite
-- the model's diagnosis (rubric item, severity, issue, explanation) is HIDDEN
to avoid biasing the reviewer.

Reviewer responds y / n / skip / quit. Results aggregate to "fraction of
rewrites the reviewer judged meaningfully better than the original phrasing"
-- the Phase 2 spec target is >=70%.

Usage:
    python -m scripts.blind_review
    python -m scripts.blind_review --run eval/runs/2026-05-21-121442.json
    python -m scripts.blind_review --seed 7   # different shuffle order

Output:
    eval/reviews/<timestamp>.json -- session record with per-pair verdicts
                                     and aggregate fraction-yes overall +
                                     per rubric_item + per severity
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _latest_run(runs_dir: Path = Path("eval/runs")) -> Path | None:
    runs = sorted(runs_dir.glob("*.json"))
    return runs[-1] if runs else None


def gather_pairs(run_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Yield one pair per finding that has a non-null suggested_rewrite.

    Pairs include the diagnosis fields (rubric_item, severity) for later
    breakdown, but those fields MUST NOT be shown to the reviewer during
    prompting.
    """
    pairs: list[dict[str, Any]] = []
    for row in run_data["per_row"]:
        for finding in row["findings"]:
            if not finding.get("suggested_rewrite"):
                continue
            pairs.append(
                {
                    "question_id": row["id"],
                    "title": row["title"],
                    "label": row["label"],
                    "rubric_item": finding["rubric_item"],
                    "severity": finding["severity"],
                    "quoted_span": finding["quoted_span"],
                    "suggested_rewrite": finding["suggested_rewrite"],
                }
            )
    return pairs


def _prompt_one(
    pair: dict[str, Any], index: int, total: int, input_fn: Callable[[str], str] = input
) -> str:
    """Show one pair and collect the reviewer's verdict. Returns yes/no/skip/quit."""
    print()
    print(f"--- [{index}/{total}] {pair['question_id']} ---")
    print(f"Question: {pair['title']}")
    print()
    print("ORIGINAL phrasing:")
    print(f"  {pair['quoted_span']}")
    print()
    print("PROPOSED rewrite:")
    print(f"  {pair['suggested_rewrite']}")
    print()
    while True:
        try:
            response = input_fn("Is the rewrite meaningfully better? [y/n/s(kip)/q(uit)]: ")
        except EOFError:
            return "quit"
        response = response.strip().lower()
        if response in ("y", "yes"):
            return "yes"
        if response in ("n", "no"):
            return "no"
        if response in ("s", "skip"):
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        print("  ... please enter y, n, s, or q")


def summarize(verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate verdicts into overall + per-rubric-item + per-severity stats."""
    yes = sum(1 for v in verdicts if v["verdict"] == "yes")
    no = sum(1 for v in verdicts if v["verdict"] == "no")
    skipped = sum(1 for v in verdicts if v["verdict"] == "skip")
    rated = yes + no

    def _bucket(key: str) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for v in verdicts:
            if v["verdict"] not in ("yes", "no"):
                continue
            b = out.setdefault(v[key], {"yes": 0, "no": 0})
            b[v["verdict"]] += 1
        for k, b in out.items():
            tot = b["yes"] + b["no"]
            b["n_rated"] = tot
            b["fraction_yes"] = b["yes"] / tot if tot else None
        return out

    return {
        "n_reviewed": rated,
        "n_yes": yes,
        "n_no": no,
        "n_skipped": skipped,
        "fraction_yes": (yes / rated) if rated else None,
        "phase2_target_pct": 70,
        "meets_phase2_target": (yes / rated >= 0.70) if rated else None,
        "by_rubric_item": _bucket("rubric_item"),
        "by_severity": _bucket("severity"),
        "by_label": _bucket("label"),
    }


def _save_session(
    verdicts: list[dict[str, Any]],
    source_run: Path,
    output_path: Path,
    seed: int,
) -> dict[str, Any]:
    summary = summarize(verdicts)
    payload = {
        "timestamp": output_path.stem,
        "source_run": str(source_run),
        "shuffle_seed": seed,
        "summary": summary,
        "verdicts": verdicts,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def print_summary(summary: dict[str, Any], output_path: Path) -> None:
    p = print
    p()
    p("=== REVIEW SUMMARY ===")
    p(
        f"Reviewed: {summary['n_reviewed']} pairs "
        f"({summary['n_yes']} better, {summary['n_no']} not better, {summary['n_skipped']} skipped)"
    )
    if summary["fraction_yes"] is None:
        p("No verdicts recorded.")
    else:
        pct = summary["fraction_yes"] * 100
        status = "PASS" if summary["meets_phase2_target"] else "BELOW"
        p(f"Fraction better: {pct:.0f}%  (Phase 2 target: 70% -- {status})")
        if summary["by_rubric_item"]:
            p("\nBy rubric item:")
            for k, b in sorted(summary["by_rubric_item"].items(), key=lambda x: -x[1]["fraction_yes"]):
                p(f"  {k:32s} {b['yes']}/{b['n_rated']} = {b['fraction_yes']*100:.0f}%")
        if summary["by_severity"]:
            p("\nBy severity:")
            for k, b in summary["by_severity"].items():
                p(f"  {k:8s} {b['yes']}/{b['n_rated']} = {b['fraction_yes']*100:.0f}%")
    p(f"\nSaved: {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=None, help="Eval run JSON; defaults to latest.")
    parser.add_argument("--out-dir", type=Path, default=Path("eval/reviews"))
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed for reproducibility.")
    args = parser.parse_args(argv)

    run_path = args.run or _latest_run()
    if run_path is None or not run_path.exists():
        print(
            "error: no eval run found. Run `python -m scripts.run_eval` first.",
            file=sys.stderr,
        )
        return 2

    run_data = json.loads(run_path.read_text(encoding="utf-8"))
    pairs = gather_pairs(run_data)
    if not pairs:
        print(
            "error: no findings with non-null suggested_rewrite in this run.",
            file=sys.stderr,
        )
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(pairs)

    print(f"Reviewing {len(pairs)} rewrite pairs from {run_path.name}")
    print("(Model diagnosis is hidden during prompting -- you only see span + rewrite.)")
    print("Commands: y = better, n = not better, s = skip, q = quit & save")

    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_path = args.out_dir / f"{timestamp}.json"

    verdicts: list[dict[str, Any]] = []
    for i, pair in enumerate(pairs, 1):
        verdict = _prompt_one(pair, i, len(pairs))
        if verdict == "quit":
            print(f"\nQuit at pair {i}/{len(pairs)}. Saving partial session.")
            break
        verdicts.append({**pair, "verdict": verdict})

    summary = _save_session(verdicts, run_path, output_path, args.seed)
    print_summary(summary, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
