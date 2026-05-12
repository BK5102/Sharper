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
            "Likelihood this issue causes a real resolution dispute. "
            "high = will almost certainly be disputed; medium = plausibly disputed; "
            "low = a clean question would still fix this."
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
