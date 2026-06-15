"""Anthropic API call that runs the rubric against a forecasting question."""

from __future__ import annotations

import os

import anthropic

from .rubric import rubric_as_prompt_block
from .schema import Critique

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_INPUT_CHARS = 4000

_SYSTEM_PROMPT_TEMPLATE = """You are Sharper, a linter for {domain_description}.

Your job is to find ambiguity, fuzzy resolution criteria, and missing operationalization in a draft question — {dispute_context}. You do NOT estimate probabilities, judge whether the question is interesting, or rewrite for style.

You evaluate the input against this rubric. Every finding must map to exactly one rubric item and quote the exact span from the input that triggered it.

# Rubric

{{rubric}}

# Rules

- Quote spans verbatim. Do not paraphrase the input — `quoted_span` must be a substring of the input.
- Be specific. "The resolution criteria are unclear" is not a finding. "The phrase 'major breakthrough' is not operationalized — no threshold for what counts as 'major'" is a finding.
- One finding per defect. Do not split a single defect across multiple rubric items.
- Rank by severity carefully:
  - **high**: very likely to cause a real dispute. Escalate to high when the criteria contain
    discretionary language ("best judgment", "best estimate", "credible sources", "as appropriate",
    "program staff will determine", "committee may decide", "some information", "approximately");
    when an undefined fuzzy term is the central decision variable ("successful", "major",
    "significant", "meaningful", "contained", "ongoing", "settle", "stable", "healthy");
    when there is no hard calendar deadline on a time-bounded question; or when the resolution
    depends on a non-persistent or unspecified source. Do not be lukewarm on defects of this
    kind — they are exactly what causes {high_severity_consequence}.
  - **medium**: a reasonable resolver would likely handle it consistently. Dispute is plausible
    only under unusual circumstances.
  - **low**: a clean question would still fix this, but unlikely to bite in practice.
- An empty `findings` list is valid output for a cleanly-written question. Do NOT invent issues to fill quota.
- If the input contains background context or resolution criteria separately, evaluate the question against ALL of it together — don't flag missing criteria if they are provided in a separate block.
- For each finding, propose a `suggested_rewrite` -- a concrete alternative phrasing that fixes the specific defect named in `issue`. The rewrite must:
  - Preserve the author's intent (what they're asking about, not just how).
  - Be a drop-in replacement for `quoted_span` (short enough to swap in directly).
  - Fix exactly the defect, no other improvements smuggled in.
  - Use concrete thresholds, named sources, hard dates -- whatever the defect requires.
  Set `suggested_rewrite` to null only when the defect is something like "no resolution criteria provided at all", where no span-level rewrite is meaningful and the question needs to be re-written from scratch."""

_MODE_PARAMS: dict[str, dict[str, str]] = {
    "default": {
        "domain_description": "forecasting questions on prediction market platforms",
        "dispute_context": "the kinds of defects that cause disputed resolutions and wasted forecaster attention",
        "high_severity_consequence": "annulments and ambiguous resolutions on prediction markets",
    },
    "civic": {
        "domain_description": (
            "structured forecasting and outcome questions used in civic planning, "
            "public health, and nonprofit program evaluation"
        ),
        "dispute_context": (
            "the kinds of defects that cause disputed program evaluations, contested outcome "
            "measurements, and vague accountability — the same underlying problem as prediction-market "
            "disputes, in a planning or program context"
        ),
        "high_severity_consequence": (
            "disputed program evaluations, contested outcome measurements, and accountability failures "
            "when funders or committees assess whether targets were met"
        ),
    },
}


def build_system_prompt(mode: str = "default") -> str:
    params = _MODE_PARAMS.get(mode, _MODE_PARAMS["default"])
    template_with_params = _SYSTEM_PROMPT_TEMPLATE.format(**params)
    return template_with_params.format(rubric=rubric_as_prompt_block(mode))


def critique_question(
    question_text: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
    mode: str = "default",
) -> Critique:
    """Run the rubric against a draft question and return a structured critique.

    mode="default" targets prediction-market questions (Metaculus-style).
    mode="civic" targets civic/nonprofit outcome and goal statements.
    """
    if not question_text.strip():
        raise ValueError("question_text is empty")
    if len(question_text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"question_text is {len(question_text)} chars; max is {MAX_INPUT_CHARS}."
        )

    client = client or anthropic.Anthropic()
    model = model or os.getenv("SHARPER_MODEL", DEFAULT_MODEL)

    response = client.messages.parse(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": build_system_prompt(mode),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Lint this question against the rubric. "
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
