"""Unit tests for the Metaculus fetcher's record transform — no network."""

from __future__ import annotations

from scripts.fetch_metaculus import _first, _to_record


def test_first_returns_first_non_null_present_key() -> None:
    d = {"a": None, "b": "found", "c": "ignored"}
    assert _first(d, "a", "b", "c") == "found"
    assert _first(d, "missing", default="fallback") == "fallback"
    assert _first(d, "a", default="fallback") == "fallback"  # null treated as missing


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
    """Newer Metaculus responses wrap question fields in a `question` sub-object."""
    raw = {
        "id": 999,
        "slug": "ai-question",
        "title": "Will AI be a big deal?",
        "question": {
            "description": "Nested background.",
            "resolution_criteria": "Resolves YES if...",
            "fine_print": "",
            "resolution": None,
            "scheduled_close_time": "2025-12-31T23:59:00Z",
            "actual_resolve_time": "2026-01-15T00:00:00Z",
        },
    }
    rec = _to_record(raw)
    assert rec["id"] == "metaculus-999"
    assert rec["title"] == "Will AI be a big deal?"
    assert rec["background"] == "Nested background."
    assert rec["resolution_criteria"].startswith("Resolves YES")
    assert rec["close_time"] == "2025-12-31T23:59:00Z"
    assert rec["resolve_time"] == "2026-01-15T00:00:00Z"


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
    """Some weird response without id — don't crash."""
    raw = {"title": "Orphan"}
    rec = _to_record(raw)
    assert rec["id"] is None
    assert rec["source_url"] is None
    assert rec["title"] == "Orphan"
