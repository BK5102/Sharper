// Real before/after examples drawn from the eval set (eval/runs/2026-05-21-121442.json).
// Three diverse rubric items so first-time visitors see what the linter actually catches.

import type { RubricItem, Severity } from "./api";

export interface Example {
  // The question text the user will lint if they click "Try this in the editor".
  question: string;
  // A short label shown above the card (not part of the question text).
  label: string;
  // The defective span the linter would flag.
  defect_span: string;
  // The model's actual suggested rewrite from the eval run.
  rewrite: string;
  rubric_item: RubricItem;
  severity: Severity;
  // Source attribution for transparency (Metaculus question ID).
  source: string;
}

export const EXAMPLES: Example[] = [
  {
    label: "Operationalization defect",
    question:
      "Will SpaceX successfully land humans on Mars by 2030?",
    defect_span: "successfully land humans on Mars",
    rewrite:
      "land at least one human astronaut on the Martian surface and return them safely to Earth, with the landing confirmed by NASA, ESA, or a peer-reviewed source",
    rubric_item: "operationalization",
    severity: "high",
    source: "hand-written example",
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
  },
];
