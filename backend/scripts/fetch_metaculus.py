"""Fetch Metaculus questions by URL/ID into a JSONL file for rubric annotation.

Why per-ID and not bulk-list:
    The /api2/questions/ list endpoint's filters are too limited to find resolved
    questions reliably (the `status` filter only accepts open/closed and is dominated
    by recent unresolved bot questions). The per-question detail endpoint works fine,
    so the workflow is:

    1. Browse metaculus.com for resolved questions — especially ones with comment
       threads where forecasters argued about the resolution (these are your
       known-ambiguous targets).
    2. Copy each question URL (or just the ID) into `data/ids.txt`, one per line.
    3. Run this script to expand them into the Sharper JSONL shape.
    4. Edit the JSONL to set `label` (`ambiguous` / `clean`) and `notes` per row.

Setup:
    Put METACULUS_API_TOKEN in backend/.env (free token at metaculus.com profile page).

Usage:
    python -m scripts.fetch_metaculus --ids-file data/ids.txt --out data/questions.metaculus.jsonl
    cat data/ids.txt | python -m scripts.fetch_metaculus --out data/questions.metaculus.jsonl
    python -m scripts.fetch_metaculus --id 1 --raw-first   # debug: dump one raw record

Each input line is either a full Metaculus question URL or just the numeric ID.
Lines beginning with `#` and blank lines are ignored.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

# Force UTF-8 on stdout so --raw-first can print question text with smart quotes,
# em-dashes, etc. on Windows consoles that default to cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_DETAIL = "https://www.metaculus.com/api2/questions/{id}/"
DEFAULT_OUT = Path("data/questions.metaculus.jsonl")
URL_ID_RE = re.compile(r"metaculus\.com/questions/(\d+)", re.IGNORECASE)


def parse_id(line: str) -> int | None:
    """Extract a numeric question ID from a URL or bare-ID line. None for blanks/comments."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.isdigit():
        return int(stripped)
    m = URL_ID_RE.search(stripped)
    if m:
        return int(m.group(1))
    return None


def _http_get(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": "sharper-fetch/0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Metaculus API {e.code} on {url}: {body}") from e


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-null value among the candidate keys."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _to_record(q: dict[str, Any]) -> dict[str, Any]:
    """Transform a raw Metaculus question into the Sharper JSONL shape.

    Handles both the legacy flat shape and the newer nested {question: {...}} shape.
    """
    inner = q.get("question") if isinstance(q.get("question"), dict) else q

    qid = _first(q, "id")
    slug = _first(q, "slug", default=None)
    source_url = (
        f"https://www.metaculus.com/questions/{qid}/{slug}/"
        if qid and slug
        else (f"https://www.metaculus.com/questions/{qid}/" if qid else None)
    )

    return {
        "id": f"metaculus-{qid}" if qid is not None else None,
        "source_url": source_url,
        "title": _first(q, "title", "question_title") or _first(inner, "title"),
        "resolution_criteria": _first(inner, "resolution_criteria", "resolution_criteria_value"),
        "background": _first(inner, "description", "background"),
        "fine_print": _first(inner, "fine_print"),
        "resolution": _first(inner, "resolution"),
        "close_time": _first(inner, "scheduled_close_time", "close_time"),
        "resolve_time": _first(
            q, "actual_resolve_time", "scheduled_resolve_time",
        ) or _first(inner, "actual_resolve_time", "scheduled_resolve_time"),
        "label": "",
        "notes": "",
    }


def fetch_by_ids(token: str, ids: Iterable[int]) -> Iterable[dict[str, Any]]:
    """Fetch each question ID via the detail endpoint. Yields raw API records."""
    for qid in ids:
        url = API_DETAIL.format(id=qid)
        yield _http_get(url, token)


def _read_ids(args: argparse.Namespace) -> list[int]:
    """Collect IDs from --id, --ids-file, or stdin (in that order)."""
    if args.id is not None:
        return [args.id]
    lines: list[str]
    if args.ids_file is not None:
        if not args.ids_file.exists():
            raise SystemExit(f"error: ids file not found: {args.ids_file}")
        lines = args.ids_file.read_text(encoding="utf-8").splitlines()
    elif not sys.stdin.isatty():
        lines = sys.stdin.read().splitlines()
    else:
        raise SystemExit(
            "error: no IDs provided. Pass --id N, --ids-file PATH, or pipe URLs/IDs on stdin."
        )
    ids: list[int] = []
    for ln in lines:
        qid = parse_id(ln)
        if qid is not None:
            ids.append(qid)
    if not ids:
        raise SystemExit("error: no valid question IDs found in input.")
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", type=int, help="Fetch a single question by ID.")
    parser.add_argument(
        "--ids-file", type=Path, help="File of question URLs/IDs, one per line."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSONL path.")
    parser.add_argument(
        "--raw-first",
        action="store_true",
        help="Print the first raw API record and exit -- useful for spotting schema changes.",
    )
    args = parser.parse_args(argv)

    load_dotenv(override=True)
    token = os.getenv("METACULUS_API_TOKEN")
    if not token:
        print(
            "error: METACULUS_API_TOKEN not set. Create an account at metaculus.com, "
            "grab your API token from the profile page, and add it to backend/.env.",
            file=sys.stderr,
        )
        return 2

    ids = _read_ids(args)

    if args.raw_first:
        first_raw = next(iter(fetch_by_ids(token, ids[:1])))
        print(json.dumps(first_raw, indent=2, ensure_ascii=False))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    with args.out.open("w", encoding="utf-8") as f:
        for raw in fetch_by_ids(token, ids):
            record = _to_record(raw)
            if not record.get("title"):
                skipped += 1
                continue
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    msg = f"wrote {written} questions to {args.out}"
    if skipped:
        msg += f" ({skipped} skipped for missing title)"
    print(msg, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
