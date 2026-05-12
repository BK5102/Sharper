"""The rubric. Edit this file to tune the linter.

Each item has a definition (what the rubric item is checking for) and example failures
(short, concrete patterns of how the failure shows up in real forecasting questions).
These are interpolated into the system prompt and are the primary lever for catching
ambiguity. If the linter's findings are too generic, sharpen the definitions and failures.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RubricSpec:
    item_id: str
    name: str
    definition: str
    example_failures: tuple[str, ...]


RUBRIC: tuple[RubricSpec, ...] = (
    RubricSpec(
        item_id="resolution_criteria_clarity",
        name="Resolution criteria clarity",
        definition=(
            "Resolution criteria must specify exactly what evidence resolves the question Yes vs No "
            "(or what value resolves a numeric/date question). A reader who has never seen the question "
            "should be able to determine the outcome from a fixed source without subjective judgment."
        ),
        example_failures=(
            "'Will AI be a big deal by 2030?' — no resolution criteria at all; 'big deal' is undefined.",
            "'Will SpaceX have a successful Mars mission by 2030?' — 'successful' is not defined; "
            "uncrewed flyby, crewed landing, and crewed return would all plausibly count.",
            "'Will the next US president be controversial?' — no objective standard for 'controversial'.",
        ),
    ),
    RubricSpec(
        item_id="time_bound_specification",
        name="Time-bound specification",
        definition=(
            "The question must specify a precise resolution moment: a calendar date, a deadline, or an "
            "event boundary. 'By 2030' is acceptable only if 'by' is defined (end of calendar year? "
            "fiscal year? before Jan 1?). Open-ended questions ('will X ever happen') need an explicit "
            "resolution cutoff or they cannot resolve No."
        ),
        example_failures=(
            "'Will humans land on Mars?' — no time bound; question can never resolve No.",
            "'Will GPT-5 launch by 2025?' — 'by 2025' is ambiguous between 'before Jan 1, 2025' and "
            "'before Dec 31, 2025'.",
            "'Will the Fed cut rates soon?' — 'soon' is not a time bound.",
        ),
    ),
    RubricSpec(
        item_id="operationalization",
        name="Operationalization of fuzzy terms",
        definition=(
            "Any subjective or fuzzy term used in the resolution criteria must be operationalized into a "
            "measurable quantity. Words like 'significant', 'major', 'widespread', 'meaningful', "
            "'successful' need explicit thresholds (e.g. '>10% adoption', 'covered by ≥3 of the NYT/WaPo/"
            "WSJ', 'death toll ≥100')."
        ),
        example_failures=(
            "'Will there be a major AI breakthrough in 2025?' — 'major' is not operationalized.",
            "'Will Apple stock significantly outperform the S&P 500?' — 'significantly' needs a numeric "
            "threshold (e.g. >5 percentage points).",
            "'Will climate change cause widespread crop failure?' — 'widespread' and 'crop failure' both "
            "need measurable definitions.",
        ),
    ),
    RubricSpec(
        item_id="edge_case_handling",
        name="Edge-case handling",
        definition=(
            "The question must say what happens in plausible edge cases: partial fulfillment, ambiguous "
            "evidence, the source disappearing, the event happening but late, etc. If reasonable "
            "interpretations could give different resolutions, the question is ambiguous."
        ),
        example_failures=(
            "'Will SpaceX launch Starship by 2025?' — silent on whether a failed launch attempt counts "
            "or whether the launch must reach orbit.",
            "'Will [politician] win the 2024 election?' — silent on what happens if the candidate "
            "withdraws or dies before election day.",
            "'Will the company report >$1B revenue in Q4?' — silent on what happens if the company "
            "restates earnings or never reports.",
        ),
    ),
    RubricSpec(
        item_id="source_authority",
        name="Source authority",
        definition=(
            "The question must name the specific source(s) used to resolve it, and those sources must be "
            "stable and authoritative. 'According to credible reports' or 'as widely reported' is not a "
            "source. The source should be one that exists at resolution time and publishes the relevant "
            "data on a known schedule."
        ),
        example_failures=(
            "'Will inflation exceed 5%?' — does not name a source (BLS CPI? Core PCE? Which release?).",
            "'Will the COVID death toll exceed X?' — 'death toll' is ambiguous between WHO, JHU, Worldometer.",
            "'According to media reports, will [event] happen?' — 'media reports' is not a specific source.",
        ),
    ),
    RubricSpec(
        item_id="scope_drift",
        name="Scope drift",
        definition=(
            "The title, background, and resolution criteria must agree on what is being asked. A common "
            "failure mode is a title that suggests one question while the resolution criteria measure "
            "something narrower or broader. Flag mismatches between what a forecaster would think they "
            "are predicting (from the title) and what the criteria actually resolve on."
        ),
        example_failures=(
            "Title 'Will AI replace radiologists?' but criteria require 'an FDA-approved AI system for a "
            "single radiology task by 2030' — the criteria are far narrower than the title.",
            "Title 'Will Bitcoin crash in 2025?' but criteria require 'BTC < $10k at any point in 2025' "
            "— defining 'crash' as a specific price is a scope decision that should be in the title.",
            "Title implies a single event but criteria allow partial credit or cumulative resolution.",
        ),
    ),
)


def rubric_as_prompt_block() -> str:
    """Render the rubric as a single text block for the system prompt."""
    lines: list[str] = []
    for spec in RUBRIC:
        lines.append(f"## {spec.name}  (id: `{spec.item_id}`)")
        lines.append("")
        lines.append(spec.definition)
        lines.append("")
        lines.append("Example failures:")
        for ex in spec.example_failures:
            lines.append(f"- {ex}")
        lines.append("")
    return "\n".join(lines).rstrip()
