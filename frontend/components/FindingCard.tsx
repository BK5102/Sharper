"use client";

import { useState } from "react";
import type { Finding } from "@/lib/api";
import { RUBRIC_ITEM_LABELS } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  finding: Finding;
  accepted: boolean;
  /**
   * Returns true if the rewrite was applied (span still present in editor),
   * false if the span no longer exists (user edited the text since linting).
   */
  onAcceptRewrite: (finding: Finding) => boolean;
}

export function FindingCard({ finding, accepted, onAcceptRewrite }: Props) {
  const [showExplanation, setShowExplanation] = useState(false);
  const [missed, setMissed] = useState(false);

  function accept() {
    const applied = onAcceptRewrite(finding);
    if (!applied) setMissed(true);
  }

  return (
    <article className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 shadow-sm">
      <header className="flex items-center justify-between gap-2 mb-3">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {RUBRIC_ITEM_LABELS[finding.rubric_item]}
        </span>
        <SeverityBadge severity={finding.severity} />
      </header>

      <p className="mb-2 text-sm text-zinc-900 dark:text-zinc-100">
        {finding.issue}
      </p>

      <div className="mb-3 rounded border-l-4 border-zinc-400 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-700 dark:text-zinc-300">
        <span className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
          Quoted span
        </span>
        {finding.quoted_span}
      </div>

      {finding.suggested_rewrite && (
        <div className="mb-3 rounded border-l-4 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-2 text-sm text-emerald-900 dark:text-emerald-100">
          <span className="block text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-1">
            Suggested rewrite
          </span>
          {finding.suggested_rewrite}
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={accept}
              disabled={accepted}
              className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-default disabled:bg-emerald-300 dark:disabled:bg-emerald-800"
            >
              {accepted ? "Accepted ✓" : "Accept rewrite"}
            </button>
            {missed && !accepted && (
              <span className="text-xs text-amber-700 dark:text-amber-400">
                Span no longer in editor — edited since lint?
              </span>
            )}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setShowExplanation((v) => !v)}
        className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
      >
        {showExplanation ? "Hide explanation" : "Show explanation"}
      </button>
      {showExplanation && (
        <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
          {finding.explanation}
        </p>
      )}
    </article>
  );
}
