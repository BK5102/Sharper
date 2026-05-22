"""Tests for the blind-reviewer protocol -- pure-function logic, no stdin needed."""

from __future__ import annotations

from scripts.blind_review import _prompt_one, gather_pairs, summarize


# ----- gather_pairs -----


def test_gather_pairs_includes_only_findings_with_rewrite() -> None:
    run_data = {
        "per_row": [
            {
                "id": "q1",
                "title": "T1",
                "label": "ambiguous",
                "findings": [
                    {
                        "rubric_item": "operationalization",
                        "severity": "high",
                        "quoted_span": "big deal",
                        "issue": "...",
                        "explanation": "...",
                        "suggested_rewrite": "achieves >=50% adoption",
                    },
                    {
                        "rubric_item": "time_bound_specification",
                        "severity": "low",
                        "quoted_span": "by 2030",
                        "issue": "...",
                        "explanation": "...",
                        "suggested_rewrite": None,  # should be filtered out
                    },
                ],
            }
        ]
    }
    pairs = gather_pairs(run_data)
    assert len(pairs) == 1
    assert pairs[0]["question_id"] == "q1"
    assert pairs[0]["rubric_item"] == "operationalization"
    assert pairs[0]["quoted_span"] == "big deal"
    assert pairs[0]["suggested_rewrite"] == "achieves >=50% adoption"


def test_gather_pairs_handles_empty_run() -> None:
    assert gather_pairs({"per_row": []}) == []


# ----- summarize -----


def _v(rubric_item: str, severity: str, label: str, verdict: str) -> dict:
    return {
        "rubric_item": rubric_item,
        "severity": severity,
        "label": label,
        "verdict": verdict,
    }


def test_summarize_overall() -> None:
    verdicts = [
        _v("operationalization", "high", "ambiguous", "yes"),
        _v("operationalization", "high", "ambiguous", "yes"),
        _v("source_authority", "medium", "ambiguous", "no"),
        _v("time_bound_specification", "low", "clean", "skip"),
    ]
    s = summarize(verdicts)
    assert s["n_yes"] == 2
    assert s["n_no"] == 1
    assert s["n_skipped"] == 1
    assert s["n_reviewed"] == 3  # yes + no, not skipped
    assert s["fraction_yes"] == 2 / 3
    assert s["meets_phase2_target"] is False  # 67% < 70%


def test_summarize_hits_phase2_target() -> None:
    verdicts = [_v("operationalization", "high", "ambiguous", "yes") for _ in range(7)]
    verdicts += [_v("operationalization", "high", "ambiguous", "no") for _ in range(3)]
    s = summarize(verdicts)
    assert s["fraction_yes"] == 0.70
    assert s["meets_phase2_target"] is True


def test_summarize_breakdown_by_rubric_item() -> None:
    verdicts = [
        _v("operationalization", "high", "ambiguous", "yes"),
        _v("operationalization", "high", "ambiguous", "yes"),
        _v("source_authority", "medium", "ambiguous", "no"),
        _v("source_authority", "medium", "ambiguous", "yes"),
    ]
    s = summarize(verdicts)
    assert s["by_rubric_item"]["operationalization"]["fraction_yes"] == 1.0
    assert s["by_rubric_item"]["source_authority"]["fraction_yes"] == 0.5


def test_summarize_breakdown_by_severity() -> None:
    verdicts = [
        _v("operationalization", "high", "ambiguous", "yes"),
        _v("source_authority", "high", "ambiguous", "no"),
        _v("time_bound_specification", "medium", "clean", "yes"),
    ]
    s = summarize(verdicts)
    assert s["by_severity"]["high"]["yes"] == 1
    assert s["by_severity"]["high"]["no"] == 1
    assert s["by_severity"]["medium"]["yes"] == 1
    assert s["by_severity"]["medium"]["n_rated"] == 1


def test_summarize_empty() -> None:
    s = summarize([])
    assert s["n_reviewed"] == 0
    assert s["fraction_yes"] is None
    assert s["meets_phase2_target"] is None


# ----- _prompt_one (with injected input fn) -----


def test_prompt_yes_response() -> None:
    pair = {
        "question_id": "q1", "title": "T", "label": "ambiguous",
        "rubric_item": "op", "severity": "high",
        "quoted_span": "x", "suggested_rewrite": "y",
    }
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "y") == "yes"
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "Y") == "yes"
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "yes") == "yes"


def test_prompt_no_response() -> None:
    pair = {"question_id": "q1", "title": "T", "label": "ambiguous",
            "rubric_item": "op", "severity": "high",
            "quoted_span": "x", "suggested_rewrite": "y"}
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "n") == "no"


def test_prompt_skip_and_quit() -> None:
    pair = {"question_id": "q1", "title": "T", "label": "ambiguous",
            "rubric_item": "op", "severity": "high",
            "quoted_span": "x", "suggested_rewrite": "y"}
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "s") == "skip"
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: "q") == "quit"


def test_prompt_retries_on_bad_input() -> None:
    """If user enters garbage, prompt asks again until they give valid input."""
    pair = {"question_id": "q1", "title": "T", "label": "ambiguous",
            "rubric_item": "op", "severity": "high",
            "quoted_span": "x", "suggested_rewrite": "y"}
    responses = iter(["maybe", "what", "y"])
    assert _prompt_one(pair, 1, 1, input_fn=lambda _: next(responses)) == "yes"


def test_prompt_eof_treated_as_quit() -> None:
    pair = {"question_id": "q1", "title": "T", "label": "ambiguous",
            "rubric_item": "op", "severity": "high",
            "quoted_span": "x", "suggested_rewrite": "y"}
    def raise_eof(_: str) -> str:
        raise EOFError
    assert _prompt_one(pair, 1, 1, input_fn=raise_eof) == "quit"
