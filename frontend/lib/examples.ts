// Examples drawn from the eval set and civic context.
// Three examples per mode shown in the gallery; mode toggle switches the set.

import type { LintMode, RubricItem, Severity } from "./api";

export interface Example {
  question: string;
  label: string;
  defect_span: string;
  rewrite: string;
  rubric_item: RubricItem;
  severity: Severity;
  source: string;
  mode: LintMode;
}

export const EXAMPLES: Example[] = [
  // --- Prediction-market examples (mode: default) ---
  {
    label: "Operationalization defect",
    question: "Will SpaceX successfully land humans on Mars by 2030?",
    defect_span: "successfully land humans on Mars",
    rewrite:
      "land at least one human astronaut on the Martian surface and return them safely to Earth, with the landing confirmed by NASA, ESA, or a peer-reviewed source",
    rubric_item: "operationalization",
    severity: "high",
    source: "hand-written example",
    mode: "default",
  },
  {
    label: "Source-authority defect",
    question:
      "Will the latest Ebola outbreak claim more than 100 lives? Resolution is by credible media report.",
    defect_span: "credible media report",
    rewrite:
      "an official declaration by the World Health Organization on its website (https://www.who.int) or in a formal WHO Situation Report",
    rubric_item: "source_authority",
    severity: "high",
    source: "Metaculus #1329 (Ebola), eval run 2026-05-21",
    mode: "default",
  },
  {
    label: "Edge-case defect",
    question:
      "Will Israel invade Lebanon before October 1, 2024, with reporting from credible sources indicating that the number of troops entering is more than 100?",
    defect_span: "reporting from credible sources",
    rewrite:
      "reporting from at least two of the following sources — AP, Reuters, AFP, BBC, or the New York Times —",
    rubric_item: "source_authority",
    severity: "high",
    source: "Metaculus #25846 (Israel-Lebanon), eval run 2026-05-21",
    mode: "default",
  },

  // --- Civic / nonprofit examples (mode: civic) ---
  {
    label: "Operationalization defect",
    question:
      "Will the City of Sacramento's housing-first program achieve a significant reduction in chronic homelessness by the end of FY2027?",
    defect_span: "significant reduction in chronic homelessness",
    rewrite:
      "a ≥15% reduction in the Point-in-Time count of chronically homeless individuals relative to the FY2024 baseline, as published in the Sacramento Housing Alliance annual enumeration",
    rubric_item: "operationalization",
    severity: "high",
    source: "civic example",
    mode: "civic",
  },
  {
    label: "Resolution criteria defect",
    question:
      "Will NDPP cohort participants achieve a successful health outcome by program exit?",
    defect_span: "achieve a successful health outcome",
    rewrite:
      "achieve an average body weight reduction of ≥5% from baseline and attend ≥9 of 12 core program sessions, as recorded in program enrollment data",
    rubric_item: "resolution_criteria_clarity",
    severity: "high",
    source: "civic example",
    mode: "civic",
  },
  {
    label: "Source-authority defect",
    question:
      "Will Sacramento issue sufficient permits to meet its RHNA housing target by 2029, according to available local data?",
    defect_span: "according to available local data",
    rewrite:
      "as reported in the City of Sacramento's Annual Progress Report submitted to the California Department of Housing and Community Development",
    rubric_item: "source_authority",
    severity: "high",
    source: "civic example",
    mode: "civic",
  },
];
