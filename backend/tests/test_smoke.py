"""Smoke tests that don't hit the network — verify imports, schemas, and prompt assembly."""

from __future__ import annotations

import json

import pytest

from sharper.critic import MAX_INPUT_CHARS, build_system_prompt, critique_question
from sharper.rubric import RUBRIC, rubric_as_prompt_block
from sharper.schema import Critique, Finding, RubricItem, Severity


def test_rubric_has_six_items() -> None:
    assert len(RUBRIC) == 6
    ids = {spec.item_id for spec in RUBRIC}
    assert ids == {item.value for item in RubricItem}


def test_every_rubric_spec_has_examples() -> None:
    for spec in RUBRIC:
        assert spec.definition.strip()
        assert len(spec.example_failures) >= 2, (
            f"{spec.item_id}: need at least 2 example failures so the model can pattern-match"
        )


def test_rubric_prompt_block_mentions_every_item() -> None:
    block = rubric_as_prompt_block()
    for spec in RUBRIC:
        assert spec.name in block
        assert spec.item_id in block


def test_rubric_civic_mode_uses_civic_examples() -> None:
    civic_block = rubric_as_prompt_block(mode="civic")
    default_block = rubric_as_prompt_block(mode="default")
    # Civic block must contain at least one civic-specific phrase not in the default block.
    assert "program evaluation" in civic_block or "housing" in civic_block
    # Each spec that has civic examples should show them in civic mode.
    for spec in RUBRIC:
        if spec.civic_example_failures:
            assert spec.civic_example_failures[0][:30] in civic_block


def test_rubric_every_spec_has_civic_examples() -> None:
    for spec in RUBRIC:
        assert len(spec.civic_example_failures) >= 2, (
            f"{spec.item_id}: need at least 2 civic example failures"
        )


def test_system_prompt_interpolates_rubric() -> None:
    prompt = build_system_prompt()
    assert "resolution_criteria_clarity" in prompt
    assert "scope_drift" in prompt
    assert "Quote spans verbatim" in prompt


def test_system_prompt_civic_mode() -> None:
    civic_prompt = build_system_prompt(mode="civic")
    default_prompt = build_system_prompt(mode="default")
    assert "civic planning" in civic_prompt
    assert "prediction market" not in civic_prompt.lower()
    # Default prompt must still mention prediction markets.
    assert "prediction market" in default_prompt


def test_critique_schema_round_trip() -> None:
    critique = Critique(
        findings=[
            Finding(
                rubric_item=RubricItem.operationalization,
                severity=Severity.high,
                quoted_span="big deal",
                issue="'big deal' is not operationalized — no measurable threshold.",
                explanation=(
                    "Without a threshold, forecasters and resolvers will disagree on what counts. "
                    "This is the canonical operationalization failure."
                ),
            )
        ],
        overall_assessment="One high-severity defect; needs operationalization before going live.",
    )
    raw = critique.model_dump_json()
    parsed = json.loads(raw)
    assert parsed["findings"][0]["rubric_item"] == "operationalization"
    assert parsed["findings"][0]["severity"] == "high"


def test_input_length_cap_rejects_oversized_input() -> None:
    too_long = "x" * (MAX_INPUT_CHARS + 1)
    with pytest.raises(ValueError, match="max is"):
        critique_question(too_long)


def test_empty_input_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        critique_question("   \n  ")
