// Typed client for the Sharper FastAPI backend. Keep types in lockstep with
// backend/sharper/schema.py -- update both when fields change.

export type Severity = "low" | "medium" | "high";
export type RubricItem =
  | "resolution_criteria_clarity"
  | "time_bound_specification"
  | "operationalization"
  | "edge_case_handling"
  | "source_authority"
  | "scope_drift";

export interface Finding {
  rubric_item: RubricItem;
  severity: Severity;
  quoted_span: string;
  issue: string;
  explanation: string;
  suggested_rewrite: string | null;
}

export interface Critique {
  findings: Finding[];
  overall_assessment: string;
}

export interface ApiError {
  status: number;
  detail: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function lint(question: string): Promise<Critique> {
  const resp = await fetch(`${API_BASE}/api/lint`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!resp.ok) {
    // FastAPI returns { detail: "..." } for 4xx; Pydantic validation returns
    // { detail: [{ loc, msg, ... }, ...] } for 422.
    let detail: string;
    try {
      const body = await resp.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : Array.isArray(body.detail)
            ? body.detail
                .map((e: { msg?: string }) => e.msg ?? JSON.stringify(e))
                .join("; ")
            : `HTTP ${resp.status}`;
    } catch {
      detail = `HTTP ${resp.status}`;
    }
    const err: ApiError = { status: resp.status, detail };
    throw err;
  }
  return (await resp.json()) as Critique;
}

export const RUBRIC_ITEM_LABELS: Record<RubricItem, string> = {
  resolution_criteria_clarity: "Resolution criteria clarity",
  time_bound_specification: "Time-bound specification",
  operationalization: "Operationalization",
  edge_case_handling: "Edge-case handling",
  source_authority: "Source authority",
  scope_drift: "Scope drift",
};
