"""Unit tests for the Metaculus fetcher's URL parsing and record transform.

No network calls -- everything tests pure-function behavior against synthetic input.
"""

from __future__ import annotations

from scripts.fetch_metaculus import _first, _to_record, parse_id


def test_first_returns_first_non_null_present_key() -> None:
    d = {"a": None, "b": "found", "c": "ignored"}
    assert _first(d, "a", "b", "c") == "found"
    assert _first(d, "missing", default="fallback") == "fallback"
    assert _first(d, "a", default="fallback") == "fallback"  # null treated as missing


def test_parse_id_accepts_bare_integer() -> None:
    assert parse_id("12345") == 12345
    assert parse_id("  42  ") == 42


def test_parse_id_extracts_from_url() -> None:
    urls = [
        "https://www.metaculus.com/questions/1/will-it-happen/",
        "https://www.metaculus.com/questions/12345/",
        "http://metaculus.com/questions/999/slug-name/",
        "metaculus.com/questions/7777/another/",
    ]
    expected = [1, 12345, 999, 7777]
    for url, want in zip(urls, expected):
        assert parse_id(url) == want, f"failed on {url}"


def test_parse_id_ignores_comments_and_blanks() -> None:
    assert parse_id("") is None
    assert parse_id("   ") is None
    assert parse_id("# comment line") is None
    assert parse_id("  # indented comment") is None


def test_parse_id_returns_none_for_garbage() -> None:
    assert parse_id("not a url or id") is None
    assert parse_id("https://example.com/questions/123/") is None  # wrong host


def test_to_record_legacy_flat_shape() -> None:
    """The /api2/questions/ endpoint historically returned flat objects."""
    raw = {
        "id": 12345,
        "slug": "will-x-happen",
        "title": "Will X happen by 2030?",
        "description": "Background text here.",
        "resolution_criteria": "Resolves YES if X happens before 2030-01-01.",
        "fine_print": "Edge cases here.",
        "resolution": 1.0,
        "close_time": "2029-12-31T23:59:00Z",
        "resolve_time": "2030-01-15T00:00:00Z",
    }
    rec = _to_record(raw)
    assert rec["id"] == "metaculus-12345"
    assert rec["source_url"] == "https://www.metaculus.com/questions/12345/will-x-happen/"
    assert rec["title"] == "Will X happen by 2030?"
    assert rec["resolution_criteria"].startswith("Resolves YES")
    assert rec["resolution"] == 1.0
    assert rec["label"] == ""
    assert rec["notes"] == ""


def test_to_record_nested_question_shape() -> None:
    """Current Metaculus responses wrap question fields in a `question` sub-object."""
    raw = {
        "id": 999,
        "slug": "ai-question",
        "title": "Will AI be a big deal?",
        "actual_resolve_time": "2026-01-15T00:00:00Z",
        "question": {
            "description": "Nested background.",
            "resolution_criteria": "Resolves YES if...",
            "fine_print": "",
            "resolution": "yes",
            "scheduled_close_time": "2025-12-31T23:59:00Z",
        },
    }
    rec = _to_record(raw)
    assert rec["id"] == "metaculus-999"
    assert rec["title"] == "Will AI be a big deal?"
    assert rec["background"] == "Nested background."
    assert rec["resolution_criteria"].startswith("Resolves YES")
    assert rec["close_time"] == "2025-12-31T23:59:00Z"
    assert rec["resolve_time"] == "2026-01-15T00:00:00Z"
    assert rec["resolution"] == "yes"


def test_to_record_handles_missing_optional_fields() -> None:
    """Defensive parsing: missing fields produce None, not exceptions."""
    raw = {"id": 1, "title": "Bare question"}
    rec = _to_record(raw)
    assert rec["id"] == "metaculus-1"
    assert rec["title"] == "Bare question"
    assert rec["resolution_criteria"] is None
    assert rec["background"] is None
    assert rec["source_url"] == "https://www.metaculus.com/questions/1/"  # no slug


def test_to_record_handles_no_id_gracefully() -> None:
    raw = {"title": "Orphan"}
    rec = _to_record(raw)
    assert rec["id"] is None
    assert rec["source_url"] is None
    assert rec["title"] == "Orphan"
