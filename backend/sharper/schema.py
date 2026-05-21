from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RubricItem(str, Enum):
    resolution_criteria_clarity = "resolution_criteria_clarity"
    time_bound_specification = "time_bound_specification"
    operationalization = "operationalization"
    edge_case_handling = "edge_case_handling"
    source_authority = "source_authority"
    scope_drift = "scope_drift"


class Finding(BaseModel):
    rubric_item: RubricItem = Field(description="Which rubric item this finding belongs to.")
    severity: Severity = Field(
        description=(
            "Likelihood this issue causes a real resolution dispute.\n"
            "- high: the defect is very likely to cause a real dispute. Escalate to high when "
            "the criteria contain discretionary language ('Metaculus may consider', 'best "
            "judgment', 'best estimate', 'credible sources', 'as appropriate', 'some information', "
            "'approximately'); when an undefined fuzzy term is the central decision variable "
            "('successful', 'major', 'significant', 'contained', 'ongoing'); when there is no "
            "hard calendar deadline on a time-bounded question; or when the resolution depends "
            "on a non-persistent source (e.g. a campaign archive, a tweet, an unspecified 'report').\n"
            "- medium: the defect exists but a reasonable resolver would likely handle it "
            "consistently. The question would be improved by fixing it, but a dispute is "
            "plausible only under unusual circumstances.\n"
            "- low: a clean question would still fix this, but it is unlikely to bite in practice."
        )
    )
    quoted_span: str = Field(
        description=(
            "The exact phrase or clause from the input that triggered this finding. "
            "Must be a verbatim substring of the input — no paraphrasing."
        )
    )
    issue: str = Field(
        description="One sentence naming the specific defect (not generic — tie it to the quoted span)."
    )
    explanation: str = Field(
        description=(
            "Two or three sentences explaining how this defect could cause a disputed resolution, "
            "with reference to the rubric item's definition."
        )
    )


class Critique(BaseModel):
    findings: list[Finding] = Field(
        description=(
            "All findings across all rubric items, ranked by severity descending. "
            "Empty list is valid for a cleanly-written question — do not invent issues."
        )
    )
    overall_assessment: str = Field(
        description=(
            "One or two sentences summarizing the question's readiness. "
            "If findings is empty, say so plainly."
        )
    )
