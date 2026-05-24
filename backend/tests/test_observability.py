"""Tests for the Sentry init + scrubber. No actual Sentry SDK call needed
unless we want to test idempotent init; for that we mock sentry_sdk.init."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from sharper.observability import init_sentry, scrub_question_field


# ----- scrub_question_field -------------------------------------------------


def test_scrub_replaces_question_in_dict_data() -> None:
    event = {"request": {"data": {"question": "Will AI be big?", "other": "keep"}}}
    out = scrub_question_field(event)
    assert out["request"]["data"]["question"] == "[SCRUBBED]"
    assert out["request"]["data"]["other"] == "keep"


def test_scrub_replaces_question_in_json_string_data() -> None:
    event = {
        "request": {
            "data": json.dumps({"question": "Will AI be big?", "keep": 1}),
        }
    }
    out = scrub_question_field(event)
    parsed = json.loads(out["request"]["data"])
    assert parsed["question"] == "[SCRUBBED]"
    assert parsed["keep"] == 1


def test_scrub_no_op_when_no_request() -> None:
    event = {"level": "error", "message": "boom"}
    out = scrub_question_field(event)
    assert out == event


def test_scrub_no_op_when_no_question() -> None:
    event = {"request": {"data": {"other": "x"}}}
    out = scrub_question_field(event)
    assert out["request"]["data"] == {"other": "x"}


def test_scrub_no_op_on_malformed_json_string_data() -> None:
    event = {"request": {"data": "this is not json"}}
    out = scrub_question_field(event)
    assert out["request"]["data"] == "this is not json"


def test_scrub_no_op_when_data_is_list_or_other() -> None:
    """JSON arrays / other shapes are not scrubbed -- we only know how to
    handle dicts with a question key. No crash."""
    event = {"request": {"data": [1, 2, 3]}}
    out = scrub_question_field(event)
    assert out["request"]["data"] == [1, 2, 3]


def test_scrub_returns_event_object() -> None:
    """before_send must return the event (or None to drop it)."""
    event = {"request": {"data": {"question": "x"}}}
    out = scrub_question_field(event)
    assert out is event  # in-place; returned for Sentry's API contract


# ----- init_sentry ----------------------------------------------------------


def test_init_no_op_when_dsn_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry()
    assert result is False
    assert not mock_init.called


def test_init_no_op_when_dsn_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "   ")
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry()
    assert result is False
    assert not mock_init.called


def test_init_calls_sentry_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://abc123@o12345.ingest.us.sentry.io/67890")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "production")
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry()
    assert result is True
    assert mock_init.called
    _, kwargs = mock_init.call_args
    assert kwargs["dsn"] == "https://abc123@o12345.ingest.us.sentry.io/67890"
    assert kwargs["send_default_pii"] is False
    assert kwargs["environment"] == "production"
    assert kwargs["before_send"] is scrub_question_field
    assert kwargs["traces_sample_rate"] == 0.1


def test_init_no_op_on_placeholder_dsn_with_ellipsis(monkeypatch: pytest.MonkeyPatch) -> None:
    """The .env.example default DSN has '...' as a placeholder. Don't init."""
    monkeypatch.setenv("SENTRY_DSN", "https://...@o000000.ingest.sentry.io/0000000")
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry()
    assert result is False
    assert not mock_init.called


def test_init_no_op_on_placeholder_dsn_with_angle_brackets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://<key>@<org>.ingest.sentry.io/<project>")
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry()
    assert result is False
    assert not mock_init.called


def test_init_returns_false_on_baddsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Sentry rejects the DSN, init returns False instead of crashing."""
    monkeypatch.setenv("SENTRY_DSN", "https://garbage-no-host/path")
    result = init_sentry()
    assert result is False


def test_init_picks_up_railway_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """SENTRY_ENVIRONMENT > RAILWAY_ENVIRONMENT > 'development' fallback."""
    monkeypatch.setenv("SENTRY_DSN", "https://x@y.ingest.sentry.io/1")
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    with patch("sentry_sdk.init") as mock_init:
        init_sentry()
    _, kwargs = mock_init.call_args
    assert kwargs["environment"] == "production"
