"""Fetch resolved Metaculus questions into a JSONL file for rubric annotation.

The Metaculus API requires a token (free account at metaculus.com -> profile -> API token).
Put it in `backend/.env` as `METACULUS_API_TOKEN=...`.

Usage:
    python -m scripts.fetch_metaculus --limit 50 --out data/questions.metaculus.jsonl
    python -m scripts.fetch_metaculus --limit 5 --raw-first   # debug: print first raw record

Each output record has:
    id, source_url, title, resolution_criteria, background, fine_print,
    resolution, close_time, resolve_time, label, notes

`label` and `notes` are emitted empty -- fill them in manually after fetching.
Use label values 'ambiguous' (for known-disputed) or 'clean' (cleanly resolved);
put a one-line summary of what went wrong in `notes` for ambiguous ones.

Metaculus changes the API shape periodically. If `--raw-first` shows a field name
this script doesn't recognize, edit `_to_record()` below.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

API_BASE = "https://www.metaculus.com/api2/questions/"
DEFAULT_OUT = Path("data/questions.metaculus.jsonl")


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
        raise SystemExit(f"Metaculus API {e.code}: {body}") from e


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-null value among the candidate keys."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _to_record(q: dict[str, Any]) -> dict[str, Any]:
    """Transform a raw Metaculus question into the Sharper JSONL shape.

    Tries the legacy `/api2/questions/` flat shape AND the newer nested
    {question: {...}} shape, so the script keeps working across API revisions.
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
        "resolve_time": _first(inner, "actual_resolve_time", "scheduled_resolve_time", "resolve_time"),
        "label": "",
        "notes": "",
    }


def fetch(token: str, limit: int, status: str, order_by: str) -> list[dict[str, Any]]:
    """Page through the API until we've collected `limit` records."""
    params = {
        "limit": min(100, limit),
        "status": status,
        "order_by": order_by,
    }
    url: str | None = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    out: list[dict[str, Any]] = []
    while url and len(out) < limit:
        page = _http_get(url, token)
        results = page.get("results") or []
        if not results:
            break
        out.extend(results)
        url = page.get("next")
    return out[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50, help="How many questions to fetch.")
    parser.add_argument(
        "--status",
        default="resolved",
        choices=("resolved", "closed", "open"),
        help="Filter by question status.",
    )
    parser.add_argument(
        "--order-by",
        default="-resolve_time",
        help="API order_by value (e.g. '-resolve_time' for most recently resolved).",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSONL path.")
    parser.add_argument(
        "--raw-first",
        action="store_true",
        help="Print the first raw API record and exit -- useful for spotting schema changes.",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    token = os.getenv("METACULUS_API_TOKEN")
    if not token:
        print(
            "error: METACULUS_API_TOKEN not set. Create an account at metaculus.com, "
            "grab your API token from the profile page, and add it to backend/.env.",
            file=sys.stderr,
        )
        return 2

    raw = fetch(token, limit=args.limit, status=args.status, order_by=args.order_by)
    if not raw:
        print("error: API returned no results -- check your query parameters", file=sys.stderr)
        return 1

    if args.raw_first:
        print(json.dumps(raw[0], indent=2, ensure_ascii=False))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("w", encoding="utf-8") as f:
        for q in raw:
            record = _to_record(q)
            if not record.get("title"):
                continue
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} questions to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
