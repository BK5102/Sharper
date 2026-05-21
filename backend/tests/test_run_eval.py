"""Tests for the eval harness — pure-function logic, no network."""

from __future__ import annotations

from scripts.run_eval import (
    SEVERITY_ORDER,
    at_least,
    build_question_text,
    strip_resolver_meta_notes,
    summarize,
)


# ----- strip_resolver_meta_notes -----


def test_strip_handles_none_and_empty() -> None:
    assert strip_resolver_meta_notes(None) is None
    assert strip_resolver_meta_notes("") == ""


def test_strip_removes_2750_style_note() -> None:
    """Real example from question 2750: leading Note about ambiguous resolution."""
    text = (
        "Note: This question was resolved ambiguous because a clash was "
        "discovered between the title and resolution criteria.\n\n"
        "The actual question follows here."
    )
    stripped = strip_resolver_meta_notes(text)
    assert stripped == "The actual question follows here."


def test_strip_removes_clash_phrase_paragraph() -> None:
    """The 'clash was discovered between title and resolution criteria' phrase
    is the resolver's diagnosis -- catch it even without a 'Note:' prefix."""
    text = (
        "Some background here.\n\n"
        "<small>This is a replacement of a question whose title and "
        "resolution criterion clashed, and was resolved ambiguous.</small>\n\n"
        "Actual criteria below."
    )
    stripped = strip_resolver_meta_notes(text)
    assert "clash" not in (stripped or "").lower()
    assert "Actual criteria below." in (stripped or "")
    assert "Some background here." in (stripped or "")


def test_strip_preserves_legitimate_resolution_words() -> None:
    """Don't strip paragraphs that legitimately mention 'resolved' or 'resolution'."""
    text = (
        "This question will be resolved Yes if X happens before 2030.\n\n"
        "Resolution will be based on WHO data."
    )
    stripped = strip_resolver_meta_notes(text)
    assert stripped == text  # no paragraphs should be dropped


def test_strip_handles_edit_prefix() -> None:
    text = (
        "Original criteria here.\n\n"
        "EDIT: This question was annulled because no source published the data.\n\n"
        "More content."
    )
    stripped = strip_resolver_meta_notes(text)
    assert "annulled" not in (stripped or "")
    assert "Original criteria here." in (stripped or "")
    assert "More content." in (stripped or "")


def test_strip_returns_none_when_everything_was_meta() -> None:
    """If the entire criteria text is just a resolver note, return None."""
    text = "Note: This question was resolved ambiguous because of a clash."
    assert strip_resolver_meta_notes(text) is None


# ----- build_question_text -----


def test_build_question_text_concatenates_fields() -> None:
    row = {
        "title": "Will X happen?",
        "resolution_criteria": "Resolves YES if X.",
        "fine_print": "Edge cases.",
        "background": "Context.",
    }
    out = build_question_text(row)
    assert "Will X happen?" in out
    assert "Resolution Criteria:\nResolves YES if X." in out
    assert "Fine Print:\nEdge cases." in out
    assert "Background:\nContext." in out


def test_build_question_text_strips_meta_from_criteria() -> None:
    row = {
        "title": "Q",
        "resolution_criteria": (
            "Note: This question was resolved ambiguous because of a clash.\n\n"
            "Real criteria."
        ),
    }
    out = build_question_text(row)
    assert "ambiguous because" not in out
    assert "Real criteria." in out


def test_build_question_text_omits_missing_fields() -> None:
    row = {"title": "Only title"}
    out = build_question_text(row)
    assert out == "Only title"


# ----- at_least and summarize -----


def test_at_least_severity_filter() -> None:
    findings = [
        {"severity": "low"},
        {"severity": "medium"},
        {"severity": "high"},
        {"severity": "high"},
    ]
    assert at_least("low", findings) == 4
    assert at_least("medium", findings) == 3
    assert at_least("high", findings) == 2


def test_summarize_basic() -> None:
    results = [
        {
            "id": "q1", "label": "ambiguous", "title": "t1",
            "findings": [
                {"severity": "high", "rubric_item": "scope_drift"},
                {"severity": "low", "rubric_item": "edge_case_handling"},
            ],
        },
        {
            "id": "q2", "label": "ambiguous", "title": "t2",
            "findings": [{"severity": "medium", "rubric_item": "operationalization"}],
        },
        {
            "id": "q3", "label": "clean", "title": "t3",
            "findings": [{"severity": "low", "rubric_item": "edge_case_handling"}],
        },
    ]
    s = summarize(results)
    assert s["n_total"] == 3
    assert s["n_ambiguous"] == 2
    assert s["n_clean"] == 1
    assert s["recall"]["high"]["n_caught"] == 1
    assert s["recall"]["medium"]["n_caught"] == 2
    assert s["recall"]["low"]["n_caught"] == 2
    assert s["fp_per_clean"]["low"]["total_findings"] == 1
    assert s["fp_per_clean"]["high"]["total_findings"] == 0
    assert s["rubric_firing"]["ambiguous"]["scope_drift"] == 1
    assert s["rubric_firing"]["clean"]["edge_case_handling"] == 1
