"""Anthropic API call that runs the rubric against a forecasting question."""

from __future__ import annotations

import os

import anthropic

from .rubric import rubric_as_prompt_block
from .schema import Critique

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_INPUT_CHARS = 4000

SYSTEM_PROMPT_TEMPLATE = """You are Sharper, a linter for forecasting questions on platforms like Metaculus.

Your job is to find ambiguity, fuzzy resolution criteria, and missing operationalization in a draft question — the kinds of defects that cause disputed resolutions and wasted forecaster attention. You do NOT estimate probabilities, judge whether the question is interesting, or rewrite for style.

You evaluate the input against this rubric. Every finding must map to exactly one rubric item and quote the exact span from the input that triggered it.

# Rubric

{rubric}

# Rules

- Quote spans verbatim. Do not paraphrase the input — `quoted_span` must be a substring of the input.
- Be specific. "The resolution criteria are unclear" is not a finding. "The phrase 'major breakthrough' is not operationalized — no threshold for what counts as 'major'" is a finding.
- One finding per defect. Do not split a single defect across multiple rubric items.
- Rank by severity carefully:
  - **high**: very likely to cause a real dispute. Escalate to high when the criteria contain
    discretionary language ("Metaculus may consider", "best judgment", "best estimate",
    "credible sources", "as appropriate", "some information", "approximately"); when an
    undefined fuzzy term is the central decision variable ("successful", "major", "significant",
    "contained", "ongoing", "settle"); when there is no hard calendar deadline on a time-bounded
    question; or when the resolution depends on a non-persistent source (e.g. a campaign archive,
    a tweet, an unspecified "report"). Do not be lukewarm on defects of this kind — they are
    exactly what causes annulments and ambiguous resolutions on Metaculus.
  - **medium**: a reasonable resolver would likely handle it consistently. Dispute is plausible
    only under unusual circumstances.
  - **low**: a clean question would still fix this, but unlikely to bite in practice.
- An empty `findings` list is valid output for a cleanly-written question. Do NOT invent issues to fill quota.
- If the input contains background context or resolution criteria separately, evaluate the question against ALL of it together — don't flag missing criteria if they are provided in a separate block."""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(rubric=rubric_as_prompt_block())


def critique_question(
    question_text: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
) -> Critique:
    """Run the rubric against a draft forecasting question, return a structured critique."""
    if not question_text.strip():
        raise ValueError("question_text is empty")
    if len(question_text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"question_text is {len(question_text)} chars; max is {MAX_INPUT_CHARS}. "
            "Real Metaculus questions fit easily within this cap."
        )

    client = client or anthropic.Anthropic()
    model = model or os.getenv("SHARPER_MODEL", DEFAULT_MODEL)

    response = client.messages.parse(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": build_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Lint this forecasting question against the rubric. "
                    "Quote the exact span for every finding.\n\n"
                    f"<question>\n{question_text.strip()}\n</question>"
                ),
            }
        ],
        output_format=Critique,
    )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Model returned no parsed output (stop_reason={response.stop_reason}). "
            "Likely a refusal or schema-format failure."
        )
    return response.parsed_output
